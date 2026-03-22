# dapp_app.py (refactored, single-candidate, regime-aware trigger_map)
# Streamlit UI to build Dynamic Adaptive Policy Pathways (DAPP)
# Run:
#   streamlit run dapp_app.py

import json
import os
import sys
import importlib
import copy
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="DAPP Pathway Builder", layout="wide")

import uuid

# --------------------------
# Stable render uid (avoid plot key churn)
# --------------------------
if "render_uid" not in st.session_state:
    st.session_state["render_uid"] = str(uuid.uuid4())
render_uid = st.session_state["render_uid"]

st.title("Dynamic Adaptive Policy Pathways (DAPP) – Pathway & Scorecard Builder")

with st.expander("ℹ️ Overview"):
    st.markdown(
        """
This app uses your **backend simulator** to construct **Dynamic Adaptive Policy Pathways (DAPP)**:

- Loads defaults from **backend/config.py** (years, DEFAULT_PARAMS, `rcp_climate_params`).
- Imports simulator from **backend/src/simulation.py**.
- Lets you define **ATP thresholds**, **policy primitives**, **escalation ladder**, and **trigger→action** rules.
- Runs **Monte Carlo**, **detects ATP**, **switches policy**, and outputs **pathways** and a **scorecard**.

Extended (Two-layer / Real Option):
- A **Regime Shift** (ON→OFF) can drop the **Crop Yield** constraint when lookahead trigger conditions are met.
- NEW: **Regime-aware trigger_map (indicator→policy priority)**.
        """
    )

# -------------------------- Repo paths & imports --------------------------
st.sidebar.header("Repository paths")
backend_dir = st.sidebar.text_input("Backend dir", "backend", key="backend_dir")
src_dir = st.sidebar.text_input("Backend src dir", "backend/src", key="src_dir")
sim_dotted = st.sidebar.text_input("Simulation dotted path", "backend.src.simulation", key="sim_dotted")
cfg_dotted = st.sidebar.text_input("Config dotted path", "backend.config", key="cfg_dotted")
utils_dotted = st.sidebar.text_input("Utils dotted path", "backend.src.utils", key="utils_dotted")

for p in [backend_dir, src_dir]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _safe_import(dotted: str):
    try:
        m = importlib.import_module(dotted)
        return m, None
    except Exception as e:
        return None, repr(e)


sim, sim_err = _safe_import(sim_dotted)
cfg, cfg_err = _safe_import(cfg_dotted)
utl, utl_err = _safe_import(utils_dotted)

if sim is None:
    st.error(f"Failed to import simulator: {sim_dotted}\n{sim_err}")
    st.stop()
if cfg is None:
    st.error(f"Failed to import config: {cfg_dotted}\n{cfg_err}")
    st.stop()
if utl is None:
    st.error(f"Failed to import utils: {utils_dotted}\n{utl_err}")
    st.stop()

for req in ["simulate_year", "simulate_simulation"]:
    if not hasattr(sim, req):
        st.error(f"simulation.py must expose {req}(...)")
        st.stop()

# -------------------------- Load defaults from config --------------------------
DEFAULT_PARAMS = dict(cfg.DEFAULT_PARAMS)
rcp_climate_params = dict(cfg.rcp_climate_params)

if "years" in DEFAULT_PARAMS and isinstance(DEFAULT_PARAMS["years"], np.ndarray):
    YEARS_DEFAULT = DEFAULT_PARAMS["years"].astype(int).tolist()
else:
    YEARS_DEFAULT = list(
        range(
            int(DEFAULT_PARAMS.get("start_year", 2025)),
            int(DEFAULT_PARAMS.get("end_year", 2100)) + 1,
        )
    )

DEFAULT_INITIAL = {
    "levee_level": DEFAULT_PARAMS.get("levee_level_increment", 20.0),
    "high_temp_tolerance_level": 0.0,
    "ecosystem_level": 100.0,
    "forest_area": DEFAULT_PARAMS.get("total_area", 10000) * DEFAULT_PARAMS.get("initial_forest_area", 0.5),
    "planting_history": {},
    "resident_capacity": 0.2,
    "transportation_level": 10.0,
    "municipal_demand": DEFAULT_PARAMS.get("initial_municipal_demand", 100.0),
    "available_water": DEFAULT_PARAMS.get("max_available_water", 3000.0) * 0.5,
    "levee_investment_total": 0.0,
    "RnD_investment_total": 0.0,
    "risky_house_total": DEFAULT_PARAMS.get("house_total", 15000),
    "non_risky_house_total": 0,
    "paddy_dam_area": 0.0,
    "temp_threshold_crop": DEFAULT_PARAMS.get("temp_threshold_crop_ini", 28.0),
}

# -------------------------- Sidebar: simulation & RCP --------------------------
st.sidebar.header("Simulation settings")

years_str = st.sidebar.text_input("Years (comma or range)", f"{YEARS_DEFAULT[0]}-{YEARS_DEFAULT[-1]}", key="years_str")


def _parse_years(s: str) -> List[int]:
    s = s.strip()
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",") if x.strip()]


try:
    YEARS = _parse_years(years_str)
except Exception:
    YEARS = YEARS_DEFAULT
    st.sidebar.warning("Could not parse years. Using config default.")

rcp_opts = ["(none)"] + [str(k) for k in rcp_climate_params.keys()]
rcp_choice = st.sidebar.selectbox("RCP climate override", rcp_opts, index=0, key="rcp_choice")

params = dict(DEFAULT_PARAMS)
if rcp_choice != "(none)":
    rcp_key = float(rcp_choice)
    for k, v in rcp_climate_params[rcp_key].items():
        params[k] = v

n_scenarios = st.sidebar.number_input("Monte Carlo scenarios", min_value=1, max_value=500, value=100, step=10, key="n_scenarios")
discount_rate = st.sidebar.number_input(
    "Discount rate (NPV)", min_value=0.0, max_value=0.2, value=0.03, step=0.005, format="%.3f", key="discount_rate"
)
k_consec = st.sidebar.number_input("ATP detection: consecutive years (k)", min_value=1, max_value=10, value=2, step=1, key="k_consec")

# Seed control
use_fixed_seed = st.sidebar.checkbox("Use fixed random seed (reproducible)", value=True, key="use_fixed_seed")
base_seed = st.sidebar.number_input("Base seed", min_value=0, max_value=2_147_483_647, value=42, step=1, key="base_seed")

# ==========================
# Regime Shift (Real Option) settings
# ==========================
st.sidebar.header("Regime shift (Real Option)")

regime_mode = st.sidebar.selectbox(
    "ATP threshold regime handling",
    [
        "1) Keep Crop Yield threshold always (single regime)",
        "2) Remove Crop Yield threshold from start (single regime)",
        "3) Adaptive regime shift: ATP metrics toggle on/off stochastically (two-layer)",
    ],
    index=2,
    key="regime_mode",
)

st.sidebar.caption("Two-layer: each year, Crop Yield constraint toggles ON/OFF with probability about 1/X.")
metric_toggle_interval_years = st.sidebar.number_input(
    "Regime shift: expected toggle interval X (years)",
    min_value=1,
    max_value=200,
    value=30,
    step=1,
    key="metric_toggle_interval_years",
)
cooldown_years = st.sidebar.number_input("Regime shift: cooldown years after exercise", min_value=0, max_value=100, value=50, step=1, key="cooldown_years")
regime_switch_cost = st.sidebar.number_input(
    "Regime shift: exercise cost (currency units)",
    min_value=0.0,
    max_value=1e12,
    value=1_000_000.0,
    step=10_000.0,
    format="%.0f",
    key="regime_switch_cost",
)
policy_switch_cost = st.sidebar.number_input(
    "Policy switch: transition cost per switch (currency units)",
    min_value=0.0,
    max_value=1e12,
    value=100_000.0,
    step=10_000.0,
    format="%.0f",
    key="policy_switch_cost",
)

# -------------------------- Quick probe: discover available metrics --------------------------
@st.cache_data(show_spinner=False)
def _probe_metrics(years: List[int], init: dict, params: dict) -> List[str]:
    """Run 1-2 years with a zero-ish policy to learn output keys."""
    try:
        dummy_policy = {}
        prev = dict(init)
        keys = set(["Year"])
        for y in years[:2]:
            prev, out = sim.simulate_year(int(y), prev, dummy_policy, params)
            if isinstance(out, dict):
                out = dict(out)
                out["Year"] = int(y)
                keys.update(out.keys())
        keys = ["Year"] + sorted([k for k in keys if k != "Year"])
        return keys
    except Exception:
        return ["Year"]


available_metrics = _probe_metrics(YEARS, DEFAULT_INITIAL, params)

# -------------------------- Thresholds & policies --------------------------
st.subheader("1) ATP thresholds per indicator")
st.caption("dir: 'max' means metric must be ≤ threshold; 'min' means metric must be ≥ threshold.")

DEFAULT_THRESHOLDS = [
    {"metric": "Flood Damage", "threshold": 1_000_000.0, "dir": "max"},
    {"metric": "available_water", "threshold": 1000.0, "dir": "min"},
    {"metric": "Crop Yield", "threshold": 4_700.0, "dir": "min"},
    {"metric": "Ecosystem Level", "threshold": 70.0, "dir": "min"},
    # {"metric": "Resident Burden", "threshold": 100_000.0, "dir": "max"},
]
thresholds_df = st.data_editor(pd.DataFrame(DEFAULT_THRESHOLDS), num_rows="dynamic", key="thresholds_df")

unknown = [m for m in thresholds_df.get("metric", pd.Series([], dtype=str)).astype(str).tolist() if m and m not in available_metrics]
if unknown:
    st.warning("Some threshold metrics are NOT found in simulator outputs: " + ", ".join(sorted(set(unknown))))
    st.caption("Tip: check naming in simulation outputs; or rename threshold metrics to match output keys.")


def _thresholds_without_crop(thr_df: pd.DataFrame) -> pd.DataFrame:
    if thr_df is None or thr_df.empty:
        return thr_df
    df2 = thr_df.copy()
    df2["metric"] = df2["metric"].astype(str)
    df2 = df2[df2["metric"].str.strip() != "Crop Yield"].reset_index(drop=True)
    return df2


thresholds_crop_on = thresholds_df.copy()
thresholds_crop_off = _thresholds_without_crop(thresholds_df)

thresholds_by_regime = {
    "CropConstraintON": thresholds_crop_on,
    "CropConstraintOFF": thresholds_crop_off,
}

st.subheader("2) Policy switching decision mode")
decision_mode = st.selectbox(
    "How to choose next policy at ATP",
    [
        "Reactive: trigger_map / escalation ladder",
        "Anticipatory: lookahead window optimization",
    ],
    index=1,
    key="decision_mode",
)

st.subheader("3) Policy primitives")

col1, col2 = st.columns([2, 1])
with col1:
    PRIMITIVE_POLICIES = {
        "NoRegret-Lite": {
            "planting_trees_amount": 0,
            "house_migration_amount": 0,
            "dam_levee_construction_cost": 1,
            "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 5,
            "agricultural_RnD_cost": 0,
            "transportation_invest": 0,
        },
        "Nature-Boost": {
            "planting_trees_amount": 100,
            "house_migration_amount": 0,
            "dam_levee_construction_cost": 0,
            "paddy_dam_construction_cost": 10,
            "capacity_building_cost": 5,
            "agricultural_RnD_cost": 0,
            "transportation_invest": 0,
        },
        "Levee-Boost": {
            "planting_trees_amount": 0,
            "house_migration_amount": 0,
            "dam_levee_construction_cost": 2,
            "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 5,
            "agricultural_RnD_cost": 0,
            "transportation_invest": 0,
        },
        "AgriR&D-Boost": {
            "planting_trees_amount": 0,
            "house_migration_amount": 0,
            "dam_levee_construction_cost": 1,
            "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 5,
            "agricultural_RnD_cost": 10,
            "transportation_invest": 0,
        },
        "Relocation-Boost": {
            "planting_trees_amount": 0,
            "house_migration_amount": 100,
            "dam_levee_construction_cost": 1,
            "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 10,
            "agricultural_RnD_cost": 0,
            "transportation_invest": 0,
        },
        "All-Boost": {
            "planting_trees_amount": 100,
            "house_migration_amount": 100,
            "dam_levee_construction_cost": 2,
            "paddy_dam_construction_cost": 10,
            "capacity_building_cost": 10,
            "agricultural_RnD_cost": 10,
            "transportation_invest": 0,
        },
    }

    policies_df = pd.DataFrame(PRIMITIVE_POLICIES).T.reset_index().rename(columns={"index": "policy"})
    policies_df = st.data_editor(policies_df, num_rows="dynamic", key="policies_df")
    if "policy" in policies_df.columns:
        PRIMITIVE_POLICIES = {row["policy"]: {k: row[k] for k in policies_df.columns if k != "policy"} for _, row in policies_df.iterrows()}

DEFAULT_TRIGGER_MAP_ON = {
    "Flood Damage": "All-Boost",
    "available_water": "Nature-Boost",
    "Crop Yield": "AgriR&D-Boost",
    "Ecosystem Level": "Nature-Boost",
}
DEFAULT_TRIGGER_MAP_OFF = {
    "Flood Damage": "All-Boost",
    "available_water": "Nature-Boost",
    "Ecosystem Level": "Nature-Boost",
}

ladder_on_txt = "NoRegret-Lite,Nature-Boost,AgriR&D-Boost,Levee-Boost,Relocation-Boost,All-Boost"
ladder_off_txt = "NoRegret-Lite,Relocation-Boost,Levee-Boost,Nature-Boost,AgriR&D-Boost,All-Boost"
trig_on_df = pd.DataFrame([{"metric": k, "next_policy": v} for k, v in DEFAULT_TRIGGER_MAP_ON.items()])
trig_off_df = pd.DataFrame([{"metric": k, "next_policy": v} for k, v in DEFAULT_TRIGGER_MAP_OFF.items()])

with col2:
    if decision_mode.startswith("Reactive"):
        st.markdown("**Escalation ladder (default / ON regime)**")
        ladder_on_txt = st.text_area(
            "Ladder (ON)",
            ladder_on_txt,
            key="ladder_on_txt",
        )

        st.markdown("**Escalation ladder (OFF regime)**")
        ladder_off_txt = st.text_area(
            "Ladder (OFF)",
            ladder_off_txt,
            key="ladder_off_txt",
        )

        st.subheader("3) Trigger → policy mapping (regime-aware)")
        st.caption("最小改修ポイント：Regimeごとに「指標→次の政策（優先順位）」を変えられます。")
        tcol1, tcol2 = st.columns(2)
        with tcol1:
            st.markdown("**Regime: CropConstraintON**")
            trig_on_df = st.data_editor(
                trig_on_df,
                num_rows="dynamic",
                key="trig_on_df",
            )
        with tcol2:
            st.markdown("**Regime: CropConstraintOFF**")
            trig_off_df = st.data_editor(
                trig_off_df,
                num_rows="dynamic",
                key="trig_off_df",
            )

ladder_on = [x.strip() for x in str(ladder_on_txt).split(",") if x.strip()]
ladder_off = [x.strip() for x in str(ladder_off_txt).split(",") if x.strip()]
ladder_by_regime = {"CropConstraintON": ladder_on, "CropConstraintOFF": ladder_off}

trigger_map_on = {r["metric"]: r["next_policy"] for _, r in trig_on_df.iterrows() if r.get("metric") and r.get("next_policy")}
trigger_map_off = {r["metric"]: r["next_policy"] for _, r in trig_off_df.iterrows() if r.get("metric") and r.get("next_policy")}

trigger_map_by_regime = {"CropConstraintON": trigger_map_on, "CropConstraintOFF": trigger_map_off}

# --------------------------
# Single candidate: Nature-first only (no dropdowns)
# --------------------------
st.subheader("4) Candidate (single: Nature-first)")
CANDIDATE_NAME = "Nature-first"

# We use the ON ladder as the candidate base (OFF ladder can still be used after regime shift)
# Trigger maps are regime-aware.
st.info(
    f"Candidate is fixed to **{CANDIDATE_NAME}**. "
    "Policy ladder & trigger_map can still differ by regime."
)

lookahead_window_years = st.number_input(
    "Lookahead window (years)",
    min_value=1,
    max_value=50,
    value=30,
    step=1,
    key="lookahead_window_years",
)
lookahead_w_fail = st.slider("Lookahead weight: threshold violation", 0.0, 1.0, 0.8, 0.05, key="lookahead_w_fail")
lookahead_w_cost = st.slider("Lookahead weight: municipal cost", 0.0, 1.0, 0.2, 0.05, key="lookahead_w_cost")
lookahead_switch_penalty = float(policy_switch_cost)
st.caption(
    "Anticipatory mode uses weighted threshold violation and municipal cost over the lookahead window. "
    "Switching penalty in lookahead is tied to 'Policy switch: transition cost per switch'."
)

# -------------------------- Core helpers --------------------------
def npv(series: List[float], years: List[int], r: float) -> float:
    if not years:
        return 0.0
    y0 = years[0]
    return float(sum(v / ((1 + r) ** (y - y0)) for v, y in zip(series, years)))


def detect_atp_earliest(df: pd.DataFrame, thresholds: pd.DataFrame, k: int) -> Optional[Tuple[int, str]]:
    """
    Return (earliest_atp_start_year, metric) among all metrics.
    ATP occurs when a metric fails k consecutive years.
    """
    if "Year" not in df.columns:
        return None
    years = df["Year"].astype(int).tolist()

    best = None  # (atp_start_year, metric)
    for _, row in thresholds.iterrows():
        metric = str(row.get("metric", ""))
        if not metric or metric not in df.columns:
            continue
        thr = float(row["threshold"])
        direc = str(row["dir"]).strip().lower()

        vals = df[metric].values
        run = 0
        for i, v in enumerate(vals):
            fail = (v > thr) if direc == "max" else (v < thr)
            run = run + 1 if fail else 0
            if run >= k:
                atp_start = int(years[i - k + 1])
                cand = (atp_start, metric)
                if (best is None) or (cand[0] < best[0]):
                    best = cand
                break
    return best


def _value_or_nan(outputs: dict, key: str) -> float:
    try:
        v = outputs.get(key, np.nan)
        return float(v)
    except Exception:
        return float("nan")


def compute_pressure_from_outputs(outputs: dict, weights: Dict[str, float], thresholds_ref: pd.DataFrame) -> float:
    """
    Convert current-year outputs to a 0-1 pressure score using threshold exceedance ratio.
    Uses thresholds_ref (typically CropConstraintON thresholds) to scale exceedance.
    """
    if not weights:
        return 0.0

    thr_lookup = {}
    for _, row in thresholds_ref.iterrows():
        m = str(row.get("metric", "")).strip()
        if not m:
            continue
        try:
            thr_lookup[m] = (float(row["threshold"]), str(row["dir"]).lower().strip())
        except Exception:
            continue

    wsum = sum(abs(w) for w in weights.values())
    if wsum <= 0:
        return 0.0

    score = 0.0
    for m, w in weights.items():
        if m not in thr_lookup:
            continue
        thr, direc = thr_lookup[m]
        v = _value_or_nan(outputs, m)
        if not np.isfinite(v) or not np.isfinite(thr) or abs(thr) < 1e-12:
            continue

        if direc == "max":
            exceed = max(0.0, (v - thr) / (abs(thr) + 1e-9))
        else:
            exceed = max(0.0, (thr - v) / (abs(thr) + 1e-9))

        contrib = min(1.0, exceed)
        score += (abs(w) / wsum) * contrib

    return float(np.clip(score, 0.0, 1.0))


def _next_policy_from_regime(
    current_policy_name: str,
    atp_metric: str,
    primitives: Dict[str, dict],
    current_regime: str,
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
) -> str:
    """
    Regime-aware decision:
      1) trigger_map_by_regime[regime][metric] if available
      2) else escalate via ladder_by_regime[regime]
      3) else keep current
    """
    trig_map_reg = trigger_map_by_regime.get(current_regime)
    if trig_map_reg is None:
        trig_map_reg = trigger_map_by_regime.get("CropConstraintON")
    if trig_map_reg is None and trigger_map_by_regime:
        trig_map_reg = next(iter(trigger_map_by_regime.values()))
    if trig_map_reg is None:
        trig_map_reg = {}

    ladder_reg = ladder_by_regime.get(current_regime)
    if ladder_reg is None:
        ladder_reg = ladder_by_regime.get("CropConstraintON")
    if ladder_reg is None and ladder_by_regime:
        ladder_reg = next(iter(ladder_by_regime.values()))
    if ladder_reg is None:
        ladder_reg = []

    next_choice = trig_map_reg.get(atp_metric, None)
    if next_choice in primitives:
        return next_choice

    if ladder_reg:
        try:
            idx = ladder_reg.index(current_policy_name)
            return ladder_reg[min(idx + 1, len(ladder_reg) - 1)]
        except ValueError:
            return current_policy_name

    return current_policy_name


def _candidate_policies_from_regime(
    current_policy_name: str,
    atp_metric: str,
    primitives: Dict[str, dict],
    current_regime: str,
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
) -> List[str]:
    trig_map_reg = trigger_map_by_regime.get(current_regime)
    if trig_map_reg is None:
        trig_map_reg = trigger_map_by_regime.get("CropConstraintON")
    if trig_map_reg is None and trigger_map_by_regime:
        trig_map_reg = next(iter(trigger_map_by_regime.values()))
    if trig_map_reg is None:
        trig_map_reg = {}

    ladder_reg = ladder_by_regime.get(current_regime)
    if ladder_reg is None:
        ladder_reg = ladder_by_regime.get("CropConstraintON")
    if ladder_reg is None and ladder_by_regime:
        ladder_reg = next(iter(ladder_by_regime.values()))
    if ladder_reg is None:
        ladder_reg = []

    candidates: List[str] = [current_policy_name]

    mapped = trig_map_reg.get(atp_metric, None)
    if mapped in primitives:
        candidates.append(str(mapped))

    if ladder_reg:
        try:
            idx = ladder_reg.index(current_policy_name)
            for pnm in ladder_reg[idx + 1:]:
                if pnm in primitives:
                    candidates.append(str(pnm))
        except ValueError:
            for pnm in ladder_reg:
                if pnm in primitives:
                    candidates.append(str(pnm))

    # keep order, unique
    seen = set()
    deduped = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped


def _count_threshold_failures(df: pd.DataFrame, thresholds: pd.DataFrame) -> int:
    if df.empty or thresholds.empty:
        return 0
    fail_count = 0
    for _, row in thresholds.iterrows():
        metric = str(row.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        thr = float(row.get("threshold", np.nan))
        direc = str(row.get("dir", "")).strip().lower()
        if not np.isfinite(thr):
            continue
        vals = pd.to_numeric(df[metric], errors="coerce")
        if direc == "max":
            fail_count += int((vals > thr).sum())
        else:
            fail_count += int((vals < thr).sum())
    return int(fail_count)


def _metric_priority_from_distance(current_outputs: dict, thresholds_eval: pd.DataFrame) -> Dict[str, float]:
    """
    Build dynamic metric priorities from current distance to threshold.
    Near/over threshold => high priority, far => lower priority.
    """
    priorities: Dict[str, float] = {}
    if thresholds_eval is None or thresholds_eval.empty:
        return priorities

    near_band = 0.30  # normalized margin band where priority decays from 1.0 to floor
    floor_w = 0.20
    for _, row in thresholds_eval.iterrows():
        metric = str(row.get("metric", "")).strip()
        if not metric:
            continue
        try:
            thr = float(row.get("threshold", np.nan))
            direc = str(row.get("dir", "")).strip().lower()
            v = float(current_outputs.get(metric, np.nan))
        except Exception:
            continue
        if not np.isfinite(v) or not np.isfinite(thr):
            continue

        denom = abs(thr) + 1e-9
        # margin > 0 means still away from threshold; <= 0 means triggered/violating.
        if direc == "max":
            margin = (thr - v) / denom
        else:
            margin = (v - thr) / denom

        if margin <= 0.0:
            pr = 1.0
        else:
            pr = 1.0 - (margin / near_band)
            pr = float(np.clip(pr, floor_w, 1.0))
        priorities[metric] = float(pr)

    return priorities


def _weighted_fail_ratio(df: pd.DataFrame, thresholds: pd.DataFrame, metric_priority: Dict[str, float]) -> float:
    if df.empty or thresholds.empty:
        return 0.0

    numer = 0.0
    denom = 0.0
    for _, row in thresholds.iterrows():
        metric = str(row.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        try:
            thr = float(row.get("threshold", np.nan))
            direc = str(row.get("dir", "")).strip().lower()
        except Exception:
            continue
        if not np.isfinite(thr):
            continue

        w = float(metric_priority.get(metric, 1.0))
        vals = pd.to_numeric(df[metric], errors="coerce")
        valid = vals[np.isfinite(vals.values)]
        if valid.empty:
            continue

        if direc == "max":
            sev = ((valid - thr) / (abs(thr) + 1e-9)).clip(lower=0.0)
        else:
            sev = ((thr - valid) / (abs(thr) + 1e-9)).clip(lower=0.0)
        sev = sev.clip(upper=1.0)

        numer += float(sev.sum()) * w
        denom += float(len(valid)) * w

    if denom <= 1e-12:
        return 0.0
    return float(np.clip(numer / denom, 0.0, 1.0))


def _simulate_window_metrics(
    start_year: int,
    years: List[int],
    prev_values: dict,
    policy: dict,
    params: dict,
    thresholds_eval: pd.DataFrame,
    metric_priority: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    future_years = [int(yy) for yy in years if int(yy) > int(start_year)]
    if not future_years:
        return {"fail_ratio": 0.0, "municipal_cost_npv": 0.0}

    sim_rows: List[dict] = []
    state = copy.deepcopy(prev_values)
    for yy in future_years:
        state, out = sim.simulate_year(int(yy), state, policy, params)
        out = out.to_dict() if isinstance(out, pd.Series) else dict(out)
        out["Year"] = int(yy)
        sim_rows.append(out)

    dfw = pd.DataFrame(sim_rows)
    fail_ratio = _weighted_fail_ratio(dfw, thresholds_eval, metric_priority or {})

    yrs = dfw["Year"].astype(int).tolist() if "Year" in dfw.columns else future_years
    municipal_cost_npv = npv(dfw.get("Municipal Cost", pd.Series(np.zeros(len(dfw)))).fillna(0).tolist(), yrs, 0.0)

    return {
        "fail_ratio": float(fail_ratio),
        "municipal_cost_npv": float(municipal_cost_npv),
    }


def _minmax_norm(values: List[float]) -> List[float]:
    if not values:
        return []
    arr = np.array(values, dtype=float)
    lo = np.nanmin(arr)
    hi = np.nanmax(arr)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return [0.0 for _ in values]
    return ((arr - lo) / (hi - lo)).astype(float).tolist()


def _select_next_policy(
    decision_mode: str,
    current_policy_name: str,
    atp_metric: str,
    y: int,
    years: List[int],
    prev_values: dict,
    current_outputs: dict,
    primitives: Dict[str, dict],
    params: dict,
    current_regime: str,
    thresholds_eval: pd.DataFrame,
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    switch_penalty: float,
) -> str:
    if decision_mode.startswith("Reactive"):
        return _next_policy_from_regime(
            current_policy_name=current_policy_name,
            atp_metric=atp_metric,
            primitives=primitives,
            current_regime=current_regime,
            trigger_map_by_regime=trigger_map_by_regime,
            ladder_by_regime=ladder_by_regime,
        )

    # Anticipatory mode: evaluate all available policies regardless of ladder/trigger mapping.
    candidates = [str(pnm) for pnm in primitives.keys()]
    if current_policy_name not in candidates:
        candidates.append(str(current_policy_name))
    if not candidates:
        return current_policy_name

    metric_priority = _metric_priority_from_distance(current_outputs or {}, thresholds_eval)

    # preserve stochastic process state so lookahead probing does not perturb MC path
    rng_state = np.random.get_state()
    try:
        eval_rows = []
        years_win = [int(yy) for yy in years if int(yy) <= int(y) + int(lookahead_window_years)]
        for cand in candidates:
            metrics = _simulate_window_metrics(
                start_year=int(y),
                years=years_win,
                prev_values=prev_values,
                policy=primitives[cand],
                params=params,
                thresholds_eval=thresholds_eval,
                metric_priority=metric_priority,
            )
            eval_rows.append(
                {
                    "policy": cand,
                    "fail_ratio": metrics["fail_ratio"],
                    "municipal_cost_npv": metrics["municipal_cost_npv"],
                    "switch_flag": 0.0 if cand == current_policy_name else 1.0,
                    "switch_cost": float(switch_penalty) * (0.0 if cand == current_policy_name else 1.0),
                }
            )
    finally:
        np.random.set_state(rng_state)

    fail_norm = _minmax_norm([r["fail_ratio"] for r in eval_rows])
    cost_norm = _minmax_norm([r["municipal_cost_npv"] + r["switch_cost"] for r in eval_rows])

    w_fail = float(lookahead_weights.get("fail_ratio", 0.6))
    w_cost = float(lookahead_weights.get("municipal_cost_npv", 0.4))
    wsum = max(1e-12, w_fail + w_cost)
    w_fail, w_cost = w_fail / wsum, w_cost / wsum

    best_policy = current_policy_name
    best_score = np.inf
    for i, row in enumerate(eval_rows):
        score = (
            w_fail * fail_norm[i]
            + w_cost * cost_norm[i]
        )
        if score < best_score:
            best_score = score
            best_policy = str(row["policy"])

    return best_policy


def build_pathway_single_layer(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    thresholds: pd.DataFrame,
    trigger_map: Dict[str, str],
    ladder: List[str],
    k: int,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    lookahead_switch_penalty: float,
) -> Tuple[pd.DataFrame, List[Tuple[int, str, str]]]:
    """Single-scenario pathway with on-the-fly switching using simulate_year."""
    if not ladder:
        raise ValueError("ladder is empty")
    if ladder[0] not in primitives:
        raise ValueError(f"ladder[0] policy '{ladder[0]}' not in primitives")

    current_policy_name = ladder[0]
    current_policy = primitives[current_policy_name]
    prev_values = dict(init)
    switches: List[Tuple[int, str, str]] = []
    out_rows: List[dict] = []
    decision_start_year = int(years[0]) if years else 0

    for y in years:
        prev_values, outputs = sim.simulate_year(int(y), prev_values, current_policy, params)
        outputs = outputs.to_dict() if isinstance(outputs, pd.Series) else dict(outputs)

        outputs["Year"] = int(y)
        outputs["Policy"] = str(current_policy_name)
        outputs["Regime"] = "Single"
        outputs["NormativePressure"] = np.nan
        out_rows.append(outputs)

        df = pd.DataFrame(out_rows)
        df_seg = df[df["Year"].astype(int) >= int(decision_start_year)].copy()
        atp = detect_atp_earliest(df_seg, thresholds, k)
        if atp is not None:
            atp_year, atp_metric = atp
            if int(y) == int(atp_year) + int(k) - 1:
                next_choice = trigger_map.get(atp_metric, None)
                trigger_map_single = {"Single": dict(trigger_map)}
                ladder_single = {"Single": list(ladder)}
                if next_choice in primitives and decision_mode.startswith("Reactive"):
                    new_policy_name = str(next_choice)
                else:
                    new_policy_name = _select_next_policy(
                        decision_mode=decision_mode,
                        current_policy_name=current_policy_name,
                        atp_metric=str(atp_metric),
                        y=int(y),
                        years=years,
                        prev_values=prev_values,
                        current_outputs=outputs,
                        primitives=primitives,
                        params=params,
                        current_regime="Single",
                        thresholds_eval=thresholds,
                        trigger_map_by_regime=trigger_map_single,
                        ladder_by_regime=ladder_single,
                        lookahead_window_years=int(lookahead_window_years),
                        lookahead_weights=lookahead_weights,
                        switch_penalty=float(lookahead_switch_penalty),
                    )

                if new_policy_name != current_policy_name:
                    switches.append((int(y), str(atp_metric), str(new_policy_name)))
                    current_policy_name = new_policy_name
                    current_policy = primitives[current_policy_name]
                    decision_start_year = int(y) + 1

    return pd.DataFrame(out_rows), switches


def build_pathway_two_layer(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    thresholds_by_regime: Dict[str, pd.DataFrame],
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
    k_atp: int,
    # regime shift settings
    metric_toggle_interval_years: int,
    cooldown_years: int,
    regime_switch_cost: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    lookahead_switch_penalty: float,
) -> Tuple[pd.DataFrame, List[Tuple[int, str, str]], List[Tuple[int, str, str]], float]:
    """
    Two-layer simulation:
      - Policy layer: ATP detection under current regime thresholds.
      - Regime layer: ATP threshold metrics toggle ON/OFF with frequency ~ once per X years.
      - NEW: trigger_map and ladder can differ by regime (minimal modification objective).
    """
    ladder_on_local = ladder_by_regime.get("CropConstraintON", [])
    if not ladder_on_local:
        raise ValueError("ladder_by_regime['CropConstraintON'] is empty")
    if ladder_on_local[0] not in primitives:
        raise ValueError(f"ladder_on[0] policy '{ladder_on_local[0]}' not in primitives")

    current_policy_name = ladder_on_local[0]
    current_policy = primitives[current_policy_name]
    prev_values = dict(init)

    current_regime = "CropConstraintON"
    base_thresholds = thresholds_by_regime.get("CropConstraintON", pd.DataFrame()).copy()
    metric_names = base_thresholds.get("metric", pd.Series([], dtype=str)).astype(str).tolist()
    active_metrics = {m: True for m in metric_names}
    policy_switches: List[Tuple[int, str, str]] = []
    regime_switches: List[Tuple[int, str, str]] = []

    out_rows: List[dict] = []
    decision_start_year = int(years[0]) if years else 0

    regime_trigger_run = 0
    cooldown_left = 0

    npv_switch_cost = 0.0
    y0 = int(years[0]) if years else 0

    for y in years:
        y = int(y)
        prev_values, outputs = sim.simulate_year(y, prev_values, current_policy, params)
        outputs = outputs.to_dict() if isinstance(outputs, pd.Series) else dict(outputs)

        # --- Regime layer ---
        lookahead_fail_abs = np.nan
        lookahead_cost_abs = np.nan
        regime_trigger_met = False
        toggled_metric = None
        toggle_action = None
        if cooldown_left > 0:
            cooldown_left -= 1
        else:
            p_toggle = 1.0 / max(1, int(metric_toggle_interval_years))
            regime_trigger_met = bool(np.random.random() < p_toggle)
            regime_trigger_run = regime_trigger_run + 1 if regime_trigger_met else 0

            if regime_trigger_met:
                toggled_metric = "Crop Yield"
                if toggled_metric in active_metrics:
                    active_now = bool(active_metrics.get(toggled_metric, True))
                    active_metrics[toggled_metric] = (not active_now)
                    toggle_action = "OFF" if active_now else "ON"
                    regime_switches.append((y, toggled_metric, toggle_action))
                    current_regime = "CropConstraintON" if active_metrics.get("Crop Yield", True) else "CropConstraintOFF"
                    regime_trigger_run = 0
                    cooldown_left = int(cooldown_years)
                    decision_start_year = int(y) + 1

                    npv_switch_cost += float(regime_switch_cost) / ((1 + float(discount_rate_local)) ** (y - y0))
                else:
                    toggled_metric = None

        # --- Record ---
        outputs["Year"] = y
        outputs["Policy"] = str(current_policy_name)
        outputs["Regime"] = str(current_regime)
        outputs["NormativePressure"] = float(regime_trigger_run)
        outputs["RegimeLookaheadViolationAbs"] = float(lookahead_fail_abs) if np.isfinite(lookahead_fail_abs) else np.nan
        outputs["RegimeLookaheadMunicipalCostAbs"] = float(lookahead_cost_abs) if np.isfinite(lookahead_cost_abs) else np.nan
        outputs["RegimeTriggerMet"] = bool(regime_trigger_met)
        outputs["RegimeToggleMetric"] = str(toggled_metric) if toggled_metric is not None else ""
        outputs["RegimeToggleAction"] = str(toggle_action) if toggle_action is not None else ""
        outputs["ActiveThresholdCount"] = int(sum(1 for m in metric_names if active_metrics.get(m, False)))
        out_rows.append(outputs)

        # --- Policy layer ---
        df = pd.DataFrame(out_rows)
        df_seg = df[df["Year"].astype(int) >= int(decision_start_year)].copy()
        if base_thresholds.empty:
            thr_df = base_thresholds.copy()
        else:
            thr_df = base_thresholds[base_thresholds["metric"].astype(str).map(lambda m: bool(active_metrics.get(str(m), True)))].reset_index(drop=True)
        atp = detect_atp_earliest(df_seg, thr_df, int(k_atp))
        if atp is not None:
            atp_year, atp_metric = atp
            if y == int(atp_year) + int(k_atp) - 1:
                new_policy_name = _select_next_policy(
                    decision_mode=decision_mode,
                    current_policy_name=current_policy_name,
                    atp_metric=str(atp_metric),
                    y=int(y),
                    years=years,
                    prev_values=prev_values,
                    current_outputs=outputs,
                    primitives=primitives,
                    params=params,
                    current_regime=current_regime,
                    thresholds_eval=thr_df,
                    trigger_map_by_regime=trigger_map_by_regime,
                    ladder_by_regime=ladder_by_regime,
                    lookahead_window_years=int(lookahead_window_years),
                    lookahead_weights=lookahead_weights,
                    switch_penalty=float(lookahead_switch_penalty),
                )
                if new_policy_name != current_policy_name:
                    policy_switches.append((y, str(atp_metric), str(new_policy_name)))
                    current_policy_name = new_policy_name
                    current_policy = primitives[current_policy_name]
                    decision_start_year = int(y) + 1

    return pd.DataFrame(out_rows), policy_switches, regime_switches, float(npv_switch_cost)


def run_mc_single_layer(
    years: List[int],
    init: dict,
    ladder: List[str],
    primitives: Dict[str, dict],
    params: dict,
    thresholds: pd.DataFrame,
    trigger_map: Dict[str, str],
    k: int,
    n: int,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    lookahead_switch_penalty: float,
    rng: np.random.Generator,
) -> Tuple[List[pd.DataFrame], List[List[Tuple[int, str, str]]], List[int]]:
    series: List[pd.DataFrame] = []
    switches: List[List[Tuple[int, str, str]]] = []
    scenario_seeds: List[int] = []

    for _ in range(int(n)):
        seed_i = int(rng.integers(0, 2**32 - 1))
        scenario_seeds.append(seed_i)
        np.random.seed(seed_i)  # backend may use np.random
        df_i, sw_i = build_pathway_single_layer(
            years,
            init,
            primitives,
            params,
            thresholds,
            trigger_map,
            ladder,
            k,
            decision_mode,
            lookahead_window_years,
            lookahead_weights,
            lookahead_switch_penalty,
        )
        series.append(df_i)
        switches.append(sw_i)

    return series, switches, scenario_seeds


def run_mc_two_layer(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    thresholds_by_regime: Dict[str, pd.DataFrame],
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
    k_atp: int,
    n: int,
    # regime settings
    metric_toggle_interval_years: int,
    cooldown_years: int,
    regime_switch_cost: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    lookahead_switch_penalty: float,
    rng: np.random.Generator,
) -> Tuple[List[pd.DataFrame], List[List[Tuple[int, str, str]]], List[List[Tuple[int, str, str]]], List[float], List[int]]:
    series: List[pd.DataFrame] = []
    policy_switches_all: List[List[Tuple[int, str, str]]] = []
    regime_switches_all: List[List[Tuple[int, str, str]]] = []
    npv_costs: List[float] = []
    scenario_seeds: List[int] = []

    for _ in range(int(n)):
        seed_i = int(rng.integers(0, 2**32 - 1))
        scenario_seeds.append(seed_i)
        np.random.seed(seed_i)

        df_i, psw_i, rsw_i, npv_cost_i = build_pathway_two_layer(
            years,
            init,
            primitives,
            params,
            thresholds_by_regime,
            trigger_map_by_regime,
            ladder_by_regime,
            k_atp,
            metric_toggle_interval_years,
            cooldown_years,
            regime_switch_cost,
            discount_rate_local,
            decision_mode,
            lookahead_window_years,
            lookahead_weights,
            lookahead_switch_penalty,
        )
        series.append(df_i)
        policy_switches_all.append(psw_i)
        regime_switches_all.append(rsw_i)
        npv_costs.append(npv_cost_i)

    return series, policy_switches_all, regime_switches_all, npv_costs, scenario_seeds


def run_mc_two_layer_with_seeds(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    thresholds_by_regime: Dict[str, pd.DataFrame],
    trigger_map_by_regime: Dict[str, Dict[str, str]],
    ladder_by_regime: Dict[str, List[str]],
    k_atp: int,
    scenario_seeds: List[int],
    # regime settings
    metric_toggle_interval_years: int,
    cooldown_years: int,
    regime_switch_cost: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    lookahead_switch_penalty: float,
) -> Tuple[List[pd.DataFrame], List[List[Tuple[int, str, str]]], List[List[Tuple[int, str, str]]], List[float]]:
    series: List[pd.DataFrame] = []
    policy_switches_all: List[List[Tuple[int, str, str]]] = []
    regime_switches_all: List[List[Tuple[int, str, str]]] = []
    npv_costs: List[float] = []

    for seed_i in scenario_seeds:
        seed_i = int(seed_i) & 0xFFFFFFFF
        np.random.seed(seed_i)

        df_i, psw_i, rsw_i, npv_cost_i = build_pathway_two_layer(
            years,
            init,
            primitives,
            params,
            thresholds_by_regime,
            trigger_map_by_regime,
            ladder_by_regime,
            k_atp,
            int(metric_toggle_interval_years),
            int(cooldown_years),
            float(regime_switch_cost),
            float(discount_rate_local),
            decision_mode,
            int(lookahead_window_years),
            lookahead_weights,
            float(lookahead_switch_penalty),
        )
        series.append(df_i)
        policy_switches_all.append(psw_i)
        regime_switches_all.append(rsw_i)
        npv_costs.append(npv_cost_i)

    return series, policy_switches_all, regime_switches_all, npv_costs


def summarize_df(df: pd.DataFrame, thresholds_df_use: pd.DataFrame, discount_rate_local: float) -> dict:
    meet_all = np.ones(len(df), dtype=bool)
    for _, row in thresholds_df_use.iterrows():
        m, thr, direc = str(row["metric"]), float(row["threshold"]), str(row["dir"]).lower()
        if m not in df.columns:
            continue
        if direc == "max":
            meet_all &= (df[m] <= thr)
        else:
            meet_all &= (df[m] >= thr)

    robustness_year_share = float(meet_all.sum()) / max(1, len(df))

    years = df["Year"].astype(int).tolist() if "Year" in df.columns else list(range(len(df)))
    npv_cost = npv(df.get("Municipal Cost", pd.Series(np.zeros(len(df)))).fillna(0).tolist(), years, discount_rate_local)
    npv_damage = npv(df.get("Flood Damage", pd.Series(np.zeros(len(df)))).fillna(0).tolist(), years, discount_rate_local)

    avg_burden = float(df.get("Resident Burden", pd.Series(np.nan)).mean())
    min_eco = float(df.get("Ecosystem Level", pd.Series(np.nan)).min())
    avg_yield = float(df.get("Crop Yield", pd.Series(np.nan)).mean())
    final_levee = float(df.get("Levee Level", pd.Series(np.nan)).iloc[-1]) if "Levee Level" in df.columns else np.nan

    # ===== 追加部分 =====

    def value_at_year(metric, year):
        if metric not in df.columns:
            return np.nan
        row = df[df["Year"] == year]
        if row.empty:
            return np.nan
        return float(row[metric].iloc[0])

    # 2050 / 2100
    flood_2050 = value_at_year("Flood Damage", 2050)
    flood_2100 = value_at_year("Flood Damage", 2100)

    burden_2050 = value_at_year("Resident Burden", 2050)
    burden_2100 = value_at_year("Resident Burden", 2100)

    eco_2050 = value_at_year("Ecosystem Level", 2050)
    eco_2100 = value_at_year("Ecosystem Level", 2100)

    yield_2050 = value_at_year("Crop Yield", 2050)
    yield_2100 = value_at_year("Crop Yield", 2100)

    return {
        "Robustness": robustness_year_share,
        "NPV Municipal Cost": npv_cost,
        "NPV Flood Damage": npv_damage,
        "Avg Resident Burden": avg_burden,
        "Min Ecosystem Level": min_eco,
        "Avg Crop Yield": avg_yield,
        "Final Levee Level": final_levee,

        # 追加
        "Flood Damage 2050": flood_2050,
        "Flood Damage 2100": flood_2100,
        "Resident Burden 2050": burden_2050,
        "Resident Burden 2100": burden_2100,
        "Ecosystem Level 2050": eco_2050,
        "Ecosystem Level 2100": eco_2100,
        "Crop Yield 2050": yield_2050,
        "Crop Yield 2100": yield_2100,
    }

# --------------------------
# Run button (compute only on click)
# --------------------------
st.divider()
run_clicked = st.button("▶️ Run DAPP (Monte Carlo)", key="run_btn")

if run_clicked:
    # reproducible RNG
    rng = np.random.default_rng(int(base_seed)) if use_fixed_seed else np.random.default_rng()

    with st.status("Running Monte Carlo and constructing pathways...", expanded=True) as status:
        status.update(label=f"Simulating candidate: {CANDIDATE_NAME}")

        if regime_mode.startswith("1)"):
            thr_use = thresholds_by_regime["CropConstraintON"]
            series, policy_switches, scenario_seeds = run_mc_single_layer(
                YEARS,
                DEFAULT_INITIAL,
                ladder_by_regime["CropConstraintON"],
                PRIMITIVE_POLICIES,
                params,
                thr_use,
                trigger_map_on,  # single-layer uses one trigger map
                k_consec,
                n_scenarios,
                decision_mode=decision_mode,
                lookahead_window_years=int(lookahead_window_years),
                lookahead_weights={
                    "fail_ratio": float(lookahead_w_fail),
                    "municipal_cost_npv": float(lookahead_w_cost),
                },
                lookahead_switch_penalty=float(lookahead_switch_penalty),
                rng=rng,
            )
            regime_switches = [[] for _ in range(len(series))]
            npv_regime_costs = [0.0 for _ in range(len(series))]

        elif regime_mode.startswith("2)"):
            thr_use = thresholds_by_regime["CropConstraintOFF"]
            series, policy_switches, scenario_seeds = run_mc_single_layer(
                YEARS,
                DEFAULT_INITIAL,
                ladder_by_regime["CropConstraintOFF"],
                PRIMITIVE_POLICIES,
                params,
                thr_use,
                trigger_map_off,  # single-layer uses one trigger map
                k_consec,
                n_scenarios,
                decision_mode=decision_mode,
                lookahead_window_years=int(lookahead_window_years),
                lookahead_weights={
                    "fail_ratio": float(lookahead_w_fail),
                    "municipal_cost_npv": float(lookahead_w_cost),
                },
                lookahead_switch_penalty=float(lookahead_switch_penalty),
                rng=rng,
            )
            for df in series:
                df["Regime"] = "CropConstraintOFF"
                df["NormativePressure"] = np.nan
            regime_switches = [[] for _ in range(len(series))]
            npv_regime_costs = [0.0 for _ in range(len(series))]

        else:
            series, policy_switches, regime_switches, npv_regime_costs, scenario_seeds = run_mc_two_layer(
                YEARS,
                DEFAULT_INITIAL,
                PRIMITIVE_POLICIES,
                params,
                thresholds_by_regime,
                trigger_map_by_regime,
                ladder_by_regime,
                k_consec,
                n_scenarios,
                metric_toggle_interval_years=int(metric_toggle_interval_years),
                cooldown_years=int(cooldown_years),
                regime_switch_cost=float(regime_switch_cost),
                discount_rate_local=float(discount_rate),
                decision_mode=decision_mode,
                lookahead_window_years=int(lookahead_window_years),
                lookahead_weights={
                    "fail_ratio": float(lookahead_w_fail),
                    "municipal_cost_npv": float(lookahead_w_cost),
                },
                lookahead_switch_penalty=float(lookahead_switch_penalty),
                rng=rng,
            )

        # Scorecards
        sc_rows = []
        for i, df in enumerate(series):
            if regime_mode.startswith("1)"):
                thr_eval = thresholds_by_regime["CropConstraintON"]
            elif regime_mode.startswith("2)"):
                thr_eval = thresholds_by_regime["CropConstraintOFF"]
            else:
                # for comparability, you can choose ON or regime-dependent; we keep ON as in your earlier design
                thr_eval = thresholds_by_regime["CropConstraintON"]

            s = summarize_df(df, thr_eval, float(discount_rate))
            s["Candidate"] = CANDIDATE_NAME

            psw = policy_switches[i] if i < len(policy_switches) else []
            rsw = regime_switches[i] if i < len(regime_switches) else []
            s["#PolicySwitches"] = len(psw)
            s["#RegimeSwitches"] = len(rsw)
            s["RegimeShiftYear"] = rsw[0][0] if rsw else np.nan
            s["NPV RegimeSwitchCost"] = float(npv_regime_costs[i]) if i < len(npv_regime_costs) else 0.0
            s["#Switches"] = s["#PolicySwitches"]  # backward compatibility

            municipal_cost_series = pd.to_numeric(
                df.get("Municipal Cost", pd.Series(np.zeros(len(df)))), errors="coerce"
            ).fillna(0.0)
            policy_series = df.get("Policy", pd.Series([""] * len(df))).astype(str)
            s["Cumulative Municipal Cost"] = float(municipal_cost_series.sum())
            for pnm in sorted(PRIMITIVE_POLICIES.keys()):
                s[f"Cumulative Municipal Cost [{pnm}]"] = float(municipal_cost_series[policy_series == pnm].sum())

            s["Cumulative PolicySwitch Cost"] = float(len(psw) * float(policy_switch_cost))
            s["Cumulative RegimeShift Cost"] = float(len(rsw) * float(regime_switch_cost))
            s["Cumulative Switching Cost"] = float(s["Cumulative PolicySwitch Cost"] + s["Cumulative RegimeShift Cost"])
            s["Cumulative Total Cost"] = float(s["Cumulative Municipal Cost"] + s["Cumulative Switching Cost"])
            sc_rows.append(s)

        scorecard = pd.DataFrame(sc_rows)
        policy_cost_metrics = [f"Cumulative Municipal Cost [{pnm}]" for pnm in sorted(PRIMITIVE_POLICIES.keys())]
        metrics_to_agg = [
            "Robustness",
            "NPV Municipal Cost",
            "NPV Flood Damage",
            "Cumulative Municipal Cost",
            "Avg Resident Burden",
            "Min Ecosystem Level",
            "Avg Crop Yield",
            "Final Levee Level",
            # 追加
            "Flood Damage 2050",
            "Flood Damage 2100",
            "Resident Burden 2050",
            "Resident Burden 2100",
            "Ecosystem Level 2050",
            "Ecosystem Level 2100",
            "Crop Yield 2050",
            "Crop Yield 2100",
            "#Switches",
            "#RegimeSwitches",
            "Cumulative PolicySwitch Cost",
            "Cumulative RegimeShift Cost",
            "Cumulative Switching Cost",
            "Cumulative Total Cost",
            "NPV RegimeSwitchCost",
        ] + policy_cost_metrics

        cand_mean = scorecard.groupby("Candidate")[metrics_to_agg].mean(numeric_only=True)
        cand_var = scorecard.groupby("Candidate")[metrics_to_agg].var(numeric_only=True)

        cand_mean.columns = [c + " (mean)" for c in cand_mean.columns]
        cand_var.columns = [c + " (var)" for c in cand_var.columns]

        cand_agg = pd.concat([cand_mean, cand_var], axis=1).reset_index()

        # Persist results (so changing widgets doesn't "erase" visuals)
        st.session_state["dapp_results"] = {
            "candidate_name": CANDIDATE_NAME,
            "series": series,
            "policy_switches": policy_switches,
            "regime_switches": regime_switches,
            "npv_regime_costs": npv_regime_costs,
            "scorecard": scorecard,
            "cand_agg": cand_agg,
            "thresholds_df": thresholds_df.copy(),
            "thresholds_by_regime": {
                "CropConstraintON": thresholds_by_regime["CropConstraintON"].copy(),
                "CropConstraintOFF": thresholds_by_regime["CropConstraintOFF"].copy(),
            },
            "policies": PRIMITIVE_POLICIES,
            "years": YEARS,
            "k_consec": int(k_consec),
            "decision_mode": str(decision_mode),
            "lookahead_window_years": int(lookahead_window_years),
            "lookahead_weights": {
                "fail_ratio": float(lookahead_w_fail),
                "municipal_cost_npv": float(lookahead_w_cost),
            },
            "lookahead_switch_penalty": float(lookahead_switch_penalty),
            "discount_rate": float(discount_rate),
            "n_scenarios": int(n_scenarios),
            "params": params,
            "available_metrics": available_metrics,
            "seed": int(base_seed) if use_fixed_seed else None,
            "regime_mode": regime_mode,
            "metric_toggle_interval_years": int(metric_toggle_interval_years),
            "cooldown_years": int(cooldown_years),
            "regime_switch_cost": float(regime_switch_cost),
            "policy_switch_cost": float(policy_switch_cost),
            "trigger_map_by_regime": {
                "CropConstraintON": dict(trigger_map_by_regime["CropConstraintON"]),
                "CropConstraintOFF": dict(trigger_map_by_regime["CropConstraintOFF"]),
            },
            "ladder_by_regime": {
                "CropConstraintON": list(ladder_by_regime["CropConstraintON"]),
                "CropConstraintOFF": list(ladder_by_regime["CropConstraintOFF"]),
            },
            "scenario_seeds": list(scenario_seeds),
        }

        st.success("Run complete. Results are persisted below.")

# -------------------- Results (persisted) --------------------
st.divider()
st.header("Results (persisted)")

if "dapp_results" not in st.session_state:
    st.info("Click **Run DAPP (Monte Carlo)** to compute results.")
    st.stop()

res = st.session_state["dapp_results"]

seed_txt = f"seed={res.get('seed')}" if res.get("seed") is not None else "seed=(random)"
st.caption(f"Showing last computed results ({seed_txt}). Changing controls does NOT recompute until you click **Run**.")

scorecard = pd.DataFrame(res["scorecard"])
cand_agg = pd.DataFrame(res["cand_agg"])
series = res["series"]

st.subheader("A) Per-scenario scorecards")
st.dataframe(scorecard, use_container_width=True)

st.subheader("B) Candidate aggregate scorecard")
st.dataframe(cand_agg, use_container_width=True)

# ---------------- Visuals ----------------
import plotly.graph_objects as go
from plotly.colors import qualitative as pq

st.subheader("C) Pathway composition (stacked share by policy over time)")
years_sorted = sorted({int(y) for df in series for y in df["Year"].unique()})
policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([], dtype=str)).astype(str).unique()})
data = {p: [] for p in policy_names}
base_colorway = list(pq.Plotly)
policy_color_map = {p: base_colorway[i % len(base_colorway)] for i, p in enumerate(policy_names)}

for y in years_sorted:
    policies_this_year = []
    for df in series:
        row = df[df["Year"] == y]
        if not row.empty and "Policy" in row.columns:
            policies_this_year.append(str(row["Policy"].iloc[0]))
    total = max(1, len(policies_this_year))
    for pnm in policy_names:
        data[pnm].append(sum(1 for p in policies_this_year if p == pnm) / total)

fig = go.Figure()
for pnm in policy_names:
    fig.add_trace(
        go.Scatter(
            x=years_sorted,
            y=data[pnm],
            mode="lines",
            stackgroup="one",
            name=pnm,
            line=dict(color=policy_color_map.get(pnm)),
        )
    )
fig.update_layout(title=f"{res['candidate_name']}: policy share across scenarios", xaxis_title="Year", yaxis_title="Share")
st.plotly_chart(fig, use_container_width=True, key=f"policy_share_{render_uid}")

st.subheader("C2) Regime composition (stacked share by regime over time)")
if any(("Regime" in df.columns) for df in series):
    regime_names = sorted({r for df in series for r in df.get("Regime", pd.Series([], dtype=str)).astype(str).unique()})
    regime_color_map = {r: base_colorway[i % len(base_colorway)] for i, r in enumerate(regime_names)}
    data_r = {r: [] for r in regime_names}
    for y in years_sorted:
        regs_this_year = []
        for df in series:
            row = df[df["Year"] == y]
            if not row.empty and "Regime" in row.columns:
                regs_this_year.append(str(row["Regime"].iloc[0]))
        total = max(1, len(regs_this_year))
        for rnm in regime_names:
            data_r[rnm].append(sum(1 for r in regs_this_year if r == rnm) / total)

    fig_r = go.Figure()
    for rnm in regime_names:
        fig_r.add_trace(
            go.Scatter(
                x=years_sorted,
                y=data_r[rnm],
                mode="lines",
                stackgroup="one",
                name=rnm,
                line=dict(color=regime_color_map.get(rnm)),
            )
        )
    fig_r.update_layout(title=f"{res['candidate_name']}: regime share across scenarios", xaxis_title="Year", yaxis_title="Share")
    st.plotly_chart(fig_r, use_container_width=True, key=f"regime_share_{render_uid}")
else:
    st.info("No Regime column found in results.")

st.subheader("C3) Threshold satisfaction share over time (by indicator)")
thr_plot_df = pd.DataFrame(res.get("thresholds_df", pd.DataFrame())).copy()
if thr_plot_df.empty or not years_sorted:
    st.info("No thresholds or years available for threshold satisfaction plot.")
else:
    # Keep only valid threshold rows
    thr_rows = []
    for _, r in thr_plot_df.iterrows():
        metric = str(r.get("metric", "")).strip()
        if not metric:
            continue
        try:
            thr = float(r.get("threshold", np.nan))
        except Exception:
            thr = np.nan
        direc = str(r.get("dir", "")).strip().lower()
        if (not np.isfinite(thr)) or (direc not in {"max", "min"}):
            continue
        thr_rows.append({"metric": metric, "threshold": float(thr), "dir": direc})

    if not thr_rows:
        st.info("No valid threshold rows to plot.")
    else:
        fig_thr = go.Figure()
        ind_names = [f"{r['metric']} ({r['dir']} {r['threshold']:g})" for r in thr_rows]
        ind_color_map = {nm: base_colorway[i % len(base_colorway)] for i, nm in enumerate(ind_names)}
        c3_final_rows = []

        for i, r in enumerate(thr_rows):
            metric = str(r["metric"])
            thr = float(r["threshold"])
            direc = str(r["dir"])
            ind_name = ind_names[i]

            y_share = []
            for y in years_sorted:
                ok = 0
                den = 0
                for df in series:
                    if metric not in df.columns:
                        continue
                    row_y = df[df["Year"] == y]
                    if row_y.empty:
                        continue
                    v = pd.to_numeric(row_y[metric], errors="coerce").iloc[0]
                    if not np.isfinite(v):
                        continue
                    den += 1
                    if direc == "max":
                        ok += int(v <= thr)
                    else:
                        ok += int(v >= thr)
                y_share.append(float(ok / den) if den > 0 else np.nan)

            fig_thr.add_trace(
                go.Scatter(
                    x=years_sorted,
                    y=y_share,
                    mode="lines",
                    name=ind_name,
                    line=dict(color=ind_color_map.get(ind_name)),
                    connectgaps=False,
                )
            )
            final_share = float(y_share[-1]) if y_share and np.isfinite(y_share[-1]) else np.nan
            c3_final_rows.append(
                {
                    "Indicator": ind_name,
                    f"Final score ({years_sorted[-1]})": final_share,
                }
            )

        fig_thr.update_layout(
            title=f"{res['candidate_name']}: threshold satisfaction share by indicator",
            xaxis_title="Year",
            yaxis_title="Share meeting threshold",
            yaxis=dict(range=[0, 1], tickformat=".0%"),
        )
        st.plotly_chart(fig_thr, use_container_width=True, key=f"threshold_share_{render_uid}")
        st.caption(f"C3 final-year scores at {years_sorted[-1]}")
        st.dataframe(pd.DataFrame(c3_final_rows), use_container_width=True)

st.subheader("C4) Cost time series (mean across scenarios)")
if not years_sorted:
    st.info("No years available for cost time-series plot.")
else:
    policy_switches_res = res.get("policy_switches", [])
    regime_switches_res = res.get("regime_switches", [])
    policy_switch_cost_res = float(res.get("policy_switch_cost", 0.0))
    regime_switch_cost_res = float(res.get("regime_switch_cost", 0.0))

    municipal_mean = []
    policy_switch_mean = []
    regime_switch_mean = []
    total_mean = []

    for y in years_sorted:
        municipal_vals = []
        for df in series:
            row = df[df["Year"] == y]
            if row.empty:
                continue
            v = pd.to_numeric(row.get("Municipal Cost", pd.Series([np.nan])), errors="coerce").iloc[0]
            if np.isfinite(v):
                municipal_vals.append(float(v))
        municipal_avg = float(np.mean(municipal_vals)) if municipal_vals else 0.0

        p_switch_count = 0
        for sw in policy_switches_res:
            p_switch_count += sum(1 for e in sw if int(e[0]) == int(y))
        p_switch_avg = float(policy_switch_cost_res * p_switch_count / max(1, len(series)))

        r_switch_count = 0
        for sw in regime_switches_res:
            r_switch_count += sum(1 for e in sw if int(e[0]) == int(y))
        r_switch_avg = float(regime_switch_cost_res * r_switch_count / max(1, len(series)))

        municipal_mean.append(municipal_avg)
        policy_switch_mean.append(p_switch_avg)
        regime_switch_mean.append(r_switch_avg)
        total_mean.append(float(municipal_avg + p_switch_avg + r_switch_avg))

    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=municipal_mean, mode="lines", name="Municipal Cost (mean)"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=policy_switch_mean, mode="lines", name="Policy Switch Cost (mean)"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=regime_switch_mean, mode="lines", name="Regime Shift Cost (mean)"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=total_mean, mode="lines", name="Total Cost (mean)", line=dict(width=3)))
    fig_cost.update_layout(
        title=f"{res['candidate_name']}: mean cost time series",
        xaxis_title="Year",
        yaxis_title="Cost (currency units)",
    )
    st.plotly_chart(fig_cost, use_container_width=True, key=f"cost_timeseries_{render_uid}")

    c4_sum_municipal = float(np.nansum(municipal_mean))
    c4_sum_policy_switch = float(np.nansum(policy_switch_mean))
    c4_sum_regime_shift = float(np.nansum(regime_switch_mean))
    c4_sum_total = float(np.nansum(total_mean))
    st.caption(f"C4 total cost over {years_sorted[0]}-{years_sorted[-1]} (sum of yearly means)")
    cc1, cc2, cc3, cc4 = st.columns(4)
    cc1.metric("Municipal Sum", f"{c4_sum_municipal:,.0f}")
    cc2.metric("Policy Switch Sum", f"{c4_sum_policy_switch:,.0f}")
    cc3.metric("Regime Shift Sum", f"{c4_sum_regime_shift:,.0f}")
    cc4.metric("Total Sum", f"{c4_sum_total:,.0f}")

# ---------------- Metro maps ----------------
st.subheader("D) Metro map (time × policy pathways)")
st.caption(
    "Nodes show the share of scenarios in each policy at time buckets; "
    "lines show transition shares between buckets. Line color is fixed (no cycling)."
)

bin_size = st.slider("Time bucket (years) – policy metro map", 5, 25, 10, step=1, key="metro_bin_policy")

policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([], dtype=str)).astype(str).unique()})
y_map = {p: i for i, p in enumerate(policy_names)}

all_years = sorted({int(y) for df in series for y in df["Year"].unique()})
if all_years:
    start_y, end_y = min(all_years), max(all_years)
    buckets = list(range(start_y, end_y + 1, int(bin_size)))
    if buckets[-1] != end_y:
        buckets.append(end_y)

    nodes = {(b, p): 0 for b in buckets for p in policy_names}
    edges = {((buckets[i], a), (buckets[i + 1], b)): 0 for i in range(len(buckets) - 1) for a in policy_names for b in policy_names}

    for df in series:
        if "Policy" not in df.columns:
            continue
        df_local = df[["Year", "Policy"]].copy()
        df_local["Year"] = df_local["Year"].astype(int)

        scenario_bucket_policy = {}
        for i, b in enumerate(buckets[:-1]):
            b0, b1 = buckets[i], buckets[i + 1]
            mask = (df_local["Year"] >= b0) & (df_local["Year"] < b1)
            sub = df_local.loc[mask, "Policy"].astype(str)
            if sub.empty:
                continue
            mode_p = sub.mode().iloc[0]
            scenario_bucket_policy[b0] = mode_p
            nodes[(b0, mode_p)] += 1

        # last bucket as a point
        last_b = buckets[-1]
        sub_last = df_local.loc[df_local["Year"] >= last_b, "Policy"].astype(str)
        if not sub_last.empty:
            mode_last = sub_last.mode().iloc[0]
            scenario_bucket_policy[last_b] = mode_last
            nodes[(last_b, mode_last)] += 1

        for i in range(len(buckets) - 1):
            b0, b1 = buckets[i], buckets[i + 1]
            if b0 in scenario_bucket_policy and b1 in scenario_bucket_policy:
                a = scenario_bucket_policy[b0]
                b = scenario_bucket_policy[b1]
                edges[((b0, a), (b1, b))] += 1

    n_sims = max(1, len(series))
    node_share = {k: v / n_sims for k, v in nodes.items()}
    edge_share = {k: v / n_sims for k, v in edges.items() if v > 0}

    figm = go.Figure()
    x_map = {b: b for b in buckets}
    # Fixed line color (single color)
    fixed_line_color = "rgba(80,80,80,0.65)"

    for ((b0, a), (b1, b)), sh in edge_share.items():
        x0, y0 = x_map[b0], y_map[a]
        x1, y1 = x_map[b1], y_map[b]
        lw = max(1.2, 18 * sh)
        edge_color = policy_color_map.get(a, fixed_line_color) if a == b else fixed_line_color
        figm.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[y0, y1],
                mode="lines",
                line=dict(width=lw, color=edge_color),
                hoverinfo="text",
                text=[f"{a} → {b}<br>{b0}→{b1}<br>share={sh:.2f}"] * 2,
                showlegend=False,
            )
        )

    node_x, node_y, node_size, node_text, node_color, node_label = [], [], [], [], [], []
    for (b, p), sh in node_share.items():
        if sh <= 0:
            continue
        node_x.append(x_map[b])
        node_y.append(y_map[p])
        node_size.append(max(8, 40 * (sh**0.5)))
        node_text.append(f"{p}<br>{b}<br>share={sh:.2f}")
        node_color.append(policy_color_map.get(p, base_colorway[0]))
        node_label.append(f"{sh * 100:.0f}%")

    figm.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(size=node_size, color=node_color, line=dict(color="white", width=0.8)),
            text=node_label,
            textposition="top center",
            hovertext=node_text,
            hoverinfo="text",
            showlegend=False,
        )
    )

    figm.update_layout(
        title=f"Metro map – {res['candidate_name']} (policy)",
        xaxis_title="Year",
        yaxis=dict(tickmode="array", tickvals=list(range(len(policy_names))), ticktext=policy_names),
        xaxis=dict(range=[start_y - int(bin_size) * 0.5, end_y + int(bin_size) * 0.5]),
        height=480,
    )
    st.plotly_chart(figm, use_container_width=True, key=f"metro_policy_{render_uid}_{bin_size}")
else:
    st.info("No years found in series for metro map.")

st.subheader("D2) Metro map (time × regime pathways)")
bin_size_r = st.slider("Time bucket (years) – regime metro map", 5, 25, 10, step=1, key="metro_bin_regime")

if not any(("Regime" in df.columns) for df in series):
    st.info("No Regime column to visualize (regime shift may be off).")
else:
    regime_names = sorted({r for df in series for r in df.get("Regime", pd.Series([], dtype=str)).astype(str).unique()})
    y_map_r = {r: i for i, r in enumerate(regime_names)}

    all_years_r = sorted({int(y) for df in series for y in df["Year"].unique()})
    if all_years_r:
        start_y, end_y = min(all_years_r), max(all_years_r)
        buckets = list(range(start_y, end_y + 1, int(bin_size_r)))
        if buckets[-1] != end_y:
            buckets.append(end_y)

        nodes = {(b, r): 0 for b in buckets for r in regime_names}
        edges = {((buckets[i], a), (buckets[i + 1], b)): 0 for i in range(len(buckets) - 1) for a in regime_names for b in regime_names}

        for df in series:
            if "Regime" not in df.columns:
                continue
            df_local = df[["Year", "Regime"]].copy()
            df_local["Year"] = df_local["Year"].astype(int)

            scenario_bucket_reg = {}
            for i, b in enumerate(buckets[:-1]):
                b0, b1 = buckets[i], buckets[i + 1]
                mask = (df_local["Year"] >= b0) & (df_local["Year"] < b1)
                sub = df_local.loc[mask, "Regime"].astype(str)
                if sub.empty:
                    continue
                mode_r = sub.mode().iloc[0]
                scenario_bucket_reg[b0] = mode_r
                nodes[(b0, mode_r)] += 1

            last_b = buckets[-1]
            sub_last = df_local.loc[df_local["Year"] >= last_b, "Regime"].astype(str)
            if not sub_last.empty:
                mode_last = sub_last.mode().iloc[0]
                scenario_bucket_reg[last_b] = mode_last
                nodes[(last_b, mode_last)] += 1

            for i in range(len(buckets) - 1):
                b0, b1 = buckets[i], buckets[i + 1]
                if b0 in scenario_bucket_reg and b1 in scenario_bucket_reg:
                    a = scenario_bucket_reg[b0]
                    b = scenario_bucket_reg[b1]
                    edges[((b0, a), (b1, b))] += 1

        n_sims = max(1, len(series))
        node_share = {k: v / n_sims for k, v in nodes.items()}
        edge_share = {k: v / n_sims for k, v in edges.items() if v > 0}

        figmr = go.Figure()
        x_map = {b: b for b in buckets}
        fixed_line_color = "rgba(80,80,80,0.65)"

        for ((b0, a), (b1, b)), sh in edge_share.items():
            x0, y0 = x_map[b0], y_map_r[a]
            x1, y1 = x_map[b1], y_map_r[b]
            lw = max(1.2, 18 * sh)
            figmr.add_trace(
                go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(width=lw, color=fixed_line_color),
                    hoverinfo="text",
                    text=[f"{a} → {b}<br>{b0}→{b1}<br>share={sh:.2f}"] * 2,
                    showlegend=False,
                )
            )

        node_x, node_y, node_size, node_text, node_color, node_label = [], [], [], [], [], []
        for (b, rnm), sh in node_share.items():
            if sh <= 0:
                continue
            node_x.append(x_map[b])
            node_y.append(y_map_r[rnm])
            node_size.append(max(8, 40 * (sh**0.5)))
            node_text.append(f"{rnm}<br>{b}<br>share={sh:.2f}")
            node_color.append(regime_color_map.get(rnm, base_colorway[0]))
            node_label.append(f"{sh * 100:.0f}%")

        figmr.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                marker=dict(size=node_size, color=node_color, line=dict(color="white", width=0.8)),
                text=node_label,
                textposition="top center",
                hovertext=node_text,
                hoverinfo="text",
                showlegend=False,
            )
        )

        figmr.update_layout(
            title=f"Metro map – {res['candidate_name']} (regime)",
            xaxis_title="Year",
            yaxis=dict(tickmode="array", tickvals=list(range(len(regime_names))), ticktext=regime_names),
            xaxis=dict(range=[start_y - int(bin_size_r) * 0.5, end_y + int(bin_size_r) * 0.5]),
            height=420,
        )
        st.plotly_chart(figmr, use_container_width=True, key=f"metro_regime_{render_uid}_{bin_size_r}")

# ---------------- Exports ----------------
st.subheader("F) Export CSVs")
st.download_button(
    "Download per-scenario scorecards CSV",
    scorecard.to_csv(index=False).encode("utf-8"),
    "dapp_scorecards_per_scenario.csv",
    "text/csv",
    key="dl_scorecard",
)
st.download_button(
    "Download candidate aggregate CSV",
    cand_agg.to_csv(index=False).encode("utf-8"),
    "dapp_scorecards_candidate.csv",
    "text/csv",
    key="dl_candagg",
)

# ==========================================================
# Exercise boundary sweep (metric toggle interval sweep)
# ==========================================================
st.divider()
st.header("G) Exercise boundary sweep (metric toggle interval X)")

st.caption(
    "Sweep expected toggle interval X (years) to visualize regime-shift behavior. "
    "For fairness, all thresholds are evaluated on the SAME scenario seeds. "
    "This section is meaningful mainly for **two-layer** mode."
)

enable_sweep = st.checkbox("Enable sweep", value=False, key="enable_sweep")

if enable_sweep:
    col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
    with col_s1:
        sweep_min = st.number_input("X min (years)", min_value=1, max_value=200, value=5, step=1, key="sweep_min")
    with col_s2:
        sweep_max = st.number_input("X max (years)", min_value=1, max_value=200, value=40, step=1, key="sweep_max")
    with col_s3:
        sweep_step = st.number_input("step", min_value=1, max_value=20, value=5, step=1, key="sweep_step")

    sweep_n = st.number_input("Sweep scenarios (n)", min_value=5, max_value=500, value=min(80, int(res["n_scenarios"])), step=5, key="sweep_n")
    sweep_seed_base = st.number_input(
        "Sweep seed base",
        min_value=0,
        max_value=2_147_483_647,
        value=int(res.get("seed") or 123),
        step=1,
        key="sweep_seed_base",
    )

    if sweep_step <= 0:
        st.warning("Step must be > 0.")
    else:
        grid = []
        x = int(sweep_min)
        while x <= int(sweep_max):
            grid.append(int(x))
            x += int(sweep_step)
        grid = sorted(set(grid))

        # Pre-generate scenario seeds for fairness
        ss_rng = np.random.default_rng(int(sweep_seed_base))
        scenario_seeds = [int(ss_rng.integers(0, 2**32 - 1)) for _ in range(int(sweep_n))]

        rows = []
        st.info("Running sweep (two-layer). If your backend is slow, reduce grid or sweep_n.")

        for interval_x in grid:
            series_s, psw_s, rsw_s, npv_costs_s = run_mc_two_layer_with_seeds(
                YEARS,
                DEFAULT_INITIAL,
                PRIMITIVE_POLICIES,
                params,
                thresholds_by_regime,
                trigger_map_by_regime,
                ladder_by_regime,
                int(k_consec),
                scenario_seeds=scenario_seeds,
                metric_toggle_interval_years=int(interval_x),
                cooldown_years=int(cooldown_years),
                regime_switch_cost=float(regime_switch_cost),
                discount_rate_local=float(discount_rate),
                decision_mode=str(decision_mode),
                lookahead_window_years=int(lookahead_window_years),
                lookahead_weights={
                    "fail_ratio": float(lookahead_w_fail),
                    "municipal_cost_npv": float(lookahead_w_cost),
                },
                lookahead_switch_penalty=float(lookahead_switch_penalty),
            )

            sc_list = [summarize_df(df, thresholds_by_regime["CropConstraintON"], float(discount_rate)) for df in series_s]
            sc_df = pd.DataFrame(sc_list)

            shift_years = [int(rsw[0][0]) for rsw in rsw_s if rsw]
            shift_rate = len(shift_years) / max(1, len(rsw_s))
            shift_year_mean = float(np.mean(shift_years)) if shift_years else np.nan

            rows.append(
                {
                    "metric_toggle_interval_years": int(interval_x),
                    "regime_shift_rate": float(shift_rate),
                    "regime_shift_year_mean": shift_year_mean,
                    "Robustness_mean": float(sc_df["Robustness"].mean()),
                    "NPV Flood Damage_mean": float(sc_df["NPV Flood Damage"].mean()),
                    "NPV Municipal Cost_mean": float(sc_df["NPV Municipal Cost"].mean()),
                    "Avg Resident Burden_mean": float(sc_df["Avg Resident Burden"].mean()),
                    "Min Ecosystem Level_mean": float(sc_df["Min Ecosystem Level"].mean()),
                    "Avg Crop Yield_mean": float(sc_df["Avg Crop Yield"].mean()),
                    "NPV RegimeSwitchCost_mean": float(np.mean(npv_costs_s)) if npv_costs_s else 0.0,
                }
            )

        sweep_df = pd.DataFrame(rows).sort_values("metric_toggle_interval_years").reset_index(drop=True)

        st.subheader("Sweep table")
        st.dataframe(sweep_df, use_container_width=True)

        # --- Robust plotting: enforce numeric ---
        for c in sweep_df.columns:
            sweep_df[c] = pd.to_numeric(sweep_df[c], errors="coerce")

        st.subheader("Sweep plots (exercise boundary view)")

        # If everything is NaN (should not happen if table has values), warn explicitly
        if sweep_df["metric_toggle_interval_years"].isna().all():
            st.warning("Sweep plot skipped: 'metric_toggle_interval_years' is all NaN after numeric coercion.")
        else:
            # 1) shift rate
            fig1 = go.Figure()
            fig1.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["regime_shift_rate"],
                    mode="lines+markers",
                    name="Regime shift rate",
                )
            )
            fig1.update_layout(
                title="Shift probability vs toggle interval X",
                xaxis_title="metric_toggle_interval_years",
                yaxis_title="Regime shift rate (share of scenarios)",
            )
            st.plotly_chart(fig1, use_container_width=True, key=f"sweep_shift_rate_{render_uid}")

            # 2) mean year (may be NaN when shift_rate=0)
            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["regime_shift_year_mean"],
                    mode="lines+markers",
                    name="Mean shift year",
                )
            )
            fig2.update_layout(
                title="Mean regime shift year (when exercised)",
                xaxis_title="metric_toggle_interval_years",
                yaxis_title="Mean shift year (NaN if no exercise)",
            )
            st.plotly_chart(fig2, use_container_width=True, key=f"sweep_shift_year_{render_uid}")

            # 3) costs
            fig3 = go.Figure()
            fig3.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["NPV Flood Damage_mean"],
                    mode="lines+markers",
                    name="NPV Flood Damage",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["NPV Municipal Cost_mean"],
                    mode="lines+markers",
                    name="NPV Municipal Cost",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["NPV RegimeSwitchCost_mean"],
                    mode="lines+markers",
                    name="NPV Regime Switch Cost",
                )
            )
            fig3.update_layout(
                title="Costs vs toggle interval X (trade-offs)",
                xaxis_title="metric_toggle_interval_years",
                yaxis_title="NPV (currency units)",
            )
            st.plotly_chart(fig3, use_container_width=True, key=f"sweep_costs_{render_uid}")

            # 4) robustness
            fig4 = go.Figure()
            fig4.add_trace(
                go.Scatter(
                    x=sweep_df["metric_toggle_interval_years"],
                    y=sweep_df["Robustness_mean"],
                    mode="lines+markers",
                    name="Robustness",
                )
            )
            fig4.update_layout(
                title="Robustness vs toggle interval X",
                xaxis_title="metric_toggle_interval_years",
                yaxis_title="Robustness (year-share)",
            )
            st.plotly_chart(fig4, use_container_width=True, key=f"sweep_rob_{render_uid}")

        st.download_button(
            "Download sweep CSV",
            sweep_df.to_csv(index=False).encode("utf-8"),
            f"dapp_regime_exercise_boundary_sweep_{res['candidate_name']}.csv",
            "text/csv",
            key="dl_sweep",
        )
