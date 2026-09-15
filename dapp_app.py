# dapp_app.py – ObjectiveRegime-generalized DAPP
# Dynamic Adaptive Policy Pathways with generalized Objective Regimes.
# Run: streamlit run dapp_app.py
#
# Design principles:
#   - Objective Regime = evaluation state (what counts as success), NOT a strategy.
#   - Policy primitives are global; policy chosen per year based on state + current regime.
#   - Performance ATP: regime thresholds violated k consecutive years → policy switch.
#   - Objective ATP: ObjectiveStrain ≥ strain_threshold for min_strain_years → regime switch.
#   - MC percentages = occurrence shares of realized pathways under the adaptive rule.

import copy
import importlib
import os
import sys
import uuid
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative as pq
import streamlit as st

st.set_page_config(page_title="DAPP Pathway Builder", layout="wide")

if "render_uid" not in st.session_state:
    st.session_state["render_uid"] = str(uuid.uuid4())
render_uid = st.session_state["render_uid"]

st.title("Dynamic Adaptive Policy Pathways (DAPP) – Objective Regime-Aware Builder")

with st.expander("ℹ️ Overview"):
    st.markdown("""
**Design principles:**
- An **Objective Regime** defines *what counts as success* — it is an evaluation state, not a strategy.
- **Policy primitives** are global; the policy chosen at each time step depends on the current state, regime thresholds, and weights.
- **Performance ATP**: current regime's thresholds violated k consecutive years → policy switch.
- **Objective ATP**: ObjectiveStrain ≥ strain_threshold for min_strain_years consecutive years → regime evaluation and possible switch.
- **Monte Carlo percentages** represent *occurrence shares of realized pathways under the adaptive rule*, not the pathway itself.

**Objective Strain** is a 0–1 indicator of how strained the current objective regime is, computed from weighted threshold violations over a rolling window.
    """)

# ========================== Backend Imports ==========================
st.sidebar.header("Repository paths")
backend_dir = st.sidebar.text_input("Backend dir", "backend", key="backend_dir")
src_dir = st.sidebar.text_input("Backend src dir", "backend/src", key="src_dir")
sim_dotted = st.sidebar.text_input("Simulation dotted path", "backend.src.simulation", key="sim_dotted")
cfg_dotted = st.sidebar.text_input("Config dotted path", "backend.config", key="cfg_dotted")

for p in [backend_dir, src_dir]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _safe_import(dotted: str):
    try:
        return importlib.import_module(dotted), None
    except Exception as e:
        return None, repr(e)


sim, sim_err = _safe_import(sim_dotted)
cfg, cfg_err = _safe_import(cfg_dotted)

if sim is None:
    st.error(f"Failed to import simulator: {sim_dotted}\n{sim_err}")
    st.stop()
if cfg is None:
    st.error(f"Failed to import config: {cfg_dotted}\n{cfg_err}")
    st.stop()

for req in ["simulate_year", "simulate_simulation"]:
    if not hasattr(sim, req):
        st.error(f"simulation.py must expose {req}(...)")
        st.stop()

# ========================== Config Defaults ==========================
DEFAULT_PARAMS = dict(cfg.DEFAULT_PARAMS)
rcp_climate_params = dict(cfg.rcp_climate_params)

if "years" in DEFAULT_PARAMS and isinstance(DEFAULT_PARAMS["years"], np.ndarray):
    YEARS_DEFAULT = DEFAULT_PARAMS["years"].astype(int).tolist()
else:
    YEARS_DEFAULT = list(range(
        int(DEFAULT_PARAMS.get("start_year", 2025)),
        int(DEFAULT_PARAMS.get("end_year", 2100)) + 1,
    ))

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

# ========================== Sidebar: MC Settings ==========================
st.sidebar.header("Simulation settings")

years_str = st.sidebar.text_input(
    "Years (comma or range)", f"{YEARS_DEFAULT[0]}-{YEARS_DEFAULT[-1]}", key="years_str"
)


def _parse_years(s: str) -> List[int]:
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",") if x.strip()]


try:
    YEARS = _parse_years(years_str)
except Exception:
    YEARS = YEARS_DEFAULT
    st.sidebar.warning("Could not parse years — using config default.")

rcp_opts = ["(none)"] + [str(k) for k in rcp_climate_params.keys()]
rcp_choice = st.sidebar.selectbox("RCP climate override", rcp_opts, index=0, key="rcp_choice")

params = dict(DEFAULT_PARAMS)
if rcp_choice != "(none)":
    for k, v in rcp_climate_params[float(rcp_choice)].items():
        params[k] = v

n_scenarios = st.sidebar.number_input("Monte Carlo scenarios", 1, 500, 100, 10, key="n_scenarios")
discount_rate = st.sidebar.number_input(
    "Discount rate (NPV)", 0.0, 0.2, 0.03, 0.005, format="%.3f", key="discount_rate"
)
k_consec = st.sidebar.number_input(
    "Performance ATP: consecutive years k", 1, 10, 2, 1, key="k_consec"
)
use_fixed_seed = st.sidebar.checkbox("Use fixed random seed", value=True, key="use_fixed_seed")
base_seed = st.sidebar.number_input("Base seed", 0, 2_147_483_647, 42, 1, key="base_seed")

st.sidebar.header("Switching costs")
regime_switch_cost = st.sidebar.number_input(
    "Regime switch cost", 0.0, 1e12, 1_000_000.0, 10_000.0, format="%.0f", key="regime_switch_cost"
)
cooldown_years = st.sidebar.number_input(
    "Cooldown years after regime switch", 0, 100, 10, 1, key="cooldown_years"
)
policy_switch_cost = st.sidebar.number_input(
    "Policy switch cost", 0.0, 1e12, 100_000.0, 10_000.0, format="%.0f", key="policy_switch_cost"
)

# ========================== Quick metric probe ==========================
@st.cache_data(show_spinner=False)
def _probe_metrics(years: List[int], init: dict, params: dict) -> List[str]:
    try:
        prev = dict(init)
        keys = {"Year"}
        for y in years[:2]:
            prev, out = sim.simulate_year(int(y), prev, {}, params)
            out = out.to_dict() if isinstance(out, pd.Series) else dict(out)
            keys.update(out.keys())
        return ["Year"] + sorted(k for k in keys if k != "Year")
    except Exception:
        return ["Year"]


available_metrics = _probe_metrics(YEARS, DEFAULT_INITIAL, params)

# ========================== Objective Regime Definitions ==========================
DEFAULT_OBJECTIVE_REGIMES = {
    "Agriculture-oriented": {
        "description": "Maintain agricultural productivity while managing flood and ecosystem risks.",
        "thresholds": [
            {"metric": "Flood Damage",      "threshold": 1_000_000.0, "dir": "max", "weight": 0.35},
            {"metric": "Crop Yield",         "threshold": 4_700.0,     "dir": "min", "weight": 0.35},
            {"metric": "Ecosystem Level",    "threshold": 70.0,        "dir": "min", "weight": 0.20},
            {"metric": "Resident Burden",    "threshold": 100_000.0,   "dir": "max", "weight": 0.10},
        ],
        "strain_threshold": 0.65,
        "min_strain_years": 3,
        "next_regime_candidates": ["Safety-oriented", "Retreat-oriented"],
    },
    "Safety-oriented": {
        "description": "Prioritize flood risk reduction and resident safety over agricultural preservation.",
        "thresholds": [
            {"metric": "Flood Damage",      "threshold": 700_000.0,  "dir": "max", "weight": 0.50},
            {"metric": "Resident Burden",   "threshold": 80_000.0,   "dir": "max", "weight": 0.25},
            {"metric": "Ecosystem Level",   "threshold": 60.0,       "dir": "min", "weight": 0.15},
            {"metric": "Crop Yield",        "threshold": 4_000.0,    "dir": "min", "weight": 0.10},
        ],
        "strain_threshold": 0.70,
        "min_strain_years": 3,
        "next_regime_candidates": ["Retreat-oriented", "Agriculture-oriented"],
    },
    "Retreat-oriented": {
        "description": "Prioritize reducing exposure and avoiding long-term lock-in.",
        "thresholds": [
            {"metric": "Flood Damage",       "threshold": 800_000.0,  "dir": "max", "weight": 0.35},
            {"metric": "risky_house_total",  "threshold": 8_000.0,    "dir": "max", "weight": 0.35},
            {"metric": "Resident Burden",    "threshold": 120_000.0,  "dir": "max", "weight": 0.20},
            {"metric": "Ecosystem Level",    "threshold": 60.0,       "dir": "min", "weight": 0.10},
        ],
        "strain_threshold": 0.70,
        "min_strain_years": 3,
        "next_regime_candidates": ["Safety-oriented"],
    },
}

st.subheader("1) Objective Regime Definitions")
st.caption(
    "Each Objective Regime defines *what counts as success* via weighted thresholds. "
    "Objective ATP fires when ObjectiveStrain exceeds the regime's strain threshold for enough consecutive years."
)

n_regimes_ui = st.number_input("Number of objective regimes", 1, 6, 3, 1, key="n_regimes_ui")
_def_names = list(DEFAULT_OBJECTIVE_REGIMES.keys())
_def_data  = list(DEFAULT_OBJECTIVE_REGIMES.values())

OBJECTIVE_REGIMES: Dict[str, dict] = {}

for _ri in range(int(n_regimes_ui)):
    _dname = _def_names[_ri] if _ri < len(_def_names) else f"Regime-{_ri + 1}"
    _ddata = _def_data[_ri]  if _ri < len(_def_data)  else {
        "description": "",
        "thresholds": [{"metric": "Flood Damage", "threshold": 1_000_000.0, "dir": "max", "weight": 1.0}],
        "strain_threshold": 0.65,
        "min_strain_years": 3,
        "next_regime_candidates": [],
    }
    with st.expander(f"Regime {_ri + 1}: {_dname}", expanded=(_ri == 0)):
        _rname = st.text_input("Regime name", value=_dname, key=f"rname_{_ri}")
        _rdesc = st.text_area("Description", value=_ddata["description"], key=f"rdesc_{_ri}", height=55)

        st.markdown("**Thresholds** (metric · threshold · dir · weight)")
        st.caption("dir='max': value ≤ threshold is success.  dir='min': value ≥ threshold is success.")
        unknown_r = [
            t["metric"] for t in _ddata["thresholds"]
            if t.get("metric") and t["metric"] not in available_metrics
        ]
        if unknown_r:
            st.caption(f"⚠ Metrics not found in simulator: {', '.join(unknown_r)}")

        _rthr_df = st.data_editor(
            pd.DataFrame(_ddata["thresholds"]),
            num_rows="dynamic",
            key=f"rthr_{_ri}",
        )
        _col_a, _col_b = st.columns(2)
        with _col_a:
            _rstrain = st.number_input(
                "Strain threshold (Objective ATP trigger)",
                0.0, 1.0, float(_ddata["strain_threshold"]), 0.05, format="%.2f", key=f"rstrain_{_ri}"
            )
            _rmin = st.number_input(
                "Min consecutive strain years",
                1, 20, int(_ddata["min_strain_years"]), 1, key=f"rmin_{_ri}"
            )
        with _col_b:
            _rnext = st.text_input(
                "Next regime candidates (comma-separated names)",
                value=", ".join(_ddata["next_regime_candidates"]),
                key=f"rnext_{_ri}",
            )
            st.caption("Leave blank for terminal regime.")

        OBJECTIVE_REGIMES[_rname] = {
            "description": _rdesc,
            "thresholds": _rthr_df.to_dict("records") if not _rthr_df.empty else [],
            "strain_threshold": float(_rstrain),
            "min_strain_years": int(_rmin),
            "next_regime_candidates": [x.strip() for x in _rnext.split(",") if x.strip()],
        }

all_regime_names = list(OBJECTIVE_REGIMES.keys())

st.subheader("2) Objective Regime switching settings")
col_or1, col_or2 = st.columns(2)
with col_or1:
    initial_regime = st.selectbox(
        "Initial Objective Regime", all_regime_names,
        index=0, key="initial_regime"
    )
with col_or2:
    objective_regime_mode = st.selectbox(
        "Objective Regime switching mode",
        ["Fixed (no regime switching)", "Endogenous (ObjectiveStrain-driven switching)"],
        index=1, key="objective_regime_mode"
    )

strain_window_years = st.number_input(
    "ObjectiveStrain: rolling window (years)",
    1, 50, 10, 1, key="strain_window_years"
)
lockin_weight = st.number_input(
    "ObjectiveStrain: lock-in weight", 0.0, 1.0, 0.2, 0.05, format="%.2f", key="lockin_weight"
)

# ========================== Policy Primitives ==========================
st.subheader("3) Policy primitives")
st.caption("Policies are global — not locked to any Objective Regime.")

_PRIMITIVE_POLICIES_DEFAULT = {
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

policies_df = pd.DataFrame(_PRIMITIVE_POLICIES_DEFAULT).T.reset_index().rename(columns={"index": "policy"})
policies_df = st.data_editor(policies_df, num_rows="dynamic", key="policies_df")
if "policy" in policies_df.columns:
    PRIMITIVE_POLICIES = {
        row["policy"]: {k: row[k] for k in policies_df.columns if k != "policy"}
        for _, row in policies_df.iterrows()
    }
else:
    PRIMITIVE_POLICIES = _PRIMITIVE_POLICIES_DEFAULT

# Policy groups (for scorecard metrics)
_LOCKIN_POLICIES     = ["AgriR&D-Boost", "All-Boost"]
_IRREVERSIBLE_POLICIES = ["AgriR&D-Boost", "Levee-Boost", "Relocation-Boost", "All-Boost"]
_FLEXIBLE_POLICIES   = ["NoRegret-Lite", "Nature-Boost"]

# ========================== Policy Decision Mode ==========================
st.subheader("4) Policy decision mode")
decision_mode = st.selectbox(
    "How to choose next policy at Performance ATP",
    [
        "Reactive: escalation ladder",
        "Anticipatory: lookahead window optimization",
    ],
    index=1,
    key="decision_mode",
)

col_ld1, col_ld2 = st.columns(2)
with col_ld1:
    lookahead_window_years = st.number_input(
        "Lookahead window (years)", 1, 50, 30, 1, key="lookahead_window_years"
    )
    lookahead_w_fail = st.slider(
        "Lookahead weight: threshold violation", 0.0, 1.0, 0.8, 0.05, key="lookahead_w_fail"
    )
    lookahead_w_cost = st.slider(
        "Lookahead weight: municipal cost", 0.0, 1.0, 0.2, 0.05, key="lookahead_w_cost"
    )

with col_ld2:
    if decision_mode.startswith("Reactive"):
        ladder_txt = st.text_area(
            "Escalation ladder (comma-separated, global)",
            "NoRegret-Lite,Nature-Boost,AgriR&D-Boost,Levee-Boost,Relocation-Boost,All-Boost",
            key="ladder_txt",
        )
    else:
        ladder_txt = "NoRegret-Lite,Nature-Boost,AgriR&D-Boost,Levee-Boost,Relocation-Boost,All-Boost"
        st.info("Anticipatory mode evaluates **all** policy primitives via lookahead — no ladder needed.")

ladder_global = [x.strip() for x in str(ladder_txt).split(",") if x.strip()]

# ========================== Core Helper Functions ==========================

def npv(series: List[float], years: List[int], r: float) -> float:
    if not years:
        return 0.0
    y0 = years[0]
    return float(sum(v / ((1 + r) ** (y - y0)) for v, y in zip(series, years)))


def detect_atp_earliest(
    df: pd.DataFrame,
    thresholds: pd.DataFrame,
    k: int,
) -> Optional[Tuple[int, str]]:
    """Return (earliest_atp_start_year, metric) or None. ATP: metric fails k consecutive years."""
    if "Year" not in df.columns:
        return None
    years = df["Year"].astype(int).tolist()
    best = None
    for _, row in thresholds.iterrows():
        metric = str(row.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        thr   = float(row["threshold"])
        direc = str(row["dir"]).strip().lower()
        run   = 0
        for i, v in enumerate(df[metric].values):
            fail = (float(v) > thr) if direc == "max" else (float(v) < thr)
            run  = run + 1 if fail else 0
            if run >= k:
                atp_start = int(years[i - k + 1])
                if best is None or atp_start < best[0]:
                    best = (atp_start, metric)
                break
    return best


def _regime_thresholds_df(regime_config: dict) -> pd.DataFrame:
    """Convert regime config thresholds list → DataFrame for detect_atp_earliest."""
    return pd.DataFrame([
        {"metric": t["metric"], "threshold": float(t["threshold"]), "dir": t["dir"]}
        for t in regime_config.get("thresholds", [])
        if t.get("metric")
    ])


def compute_objective_strain(
    history_rows: List[dict],
    regime_config: dict,
    lockin_policy_names: Optional[List[str]] = None,
    window: int = 10,
    lockin_weight: float = 0.2,
) -> dict:
    """
    Compute 0-1 ObjectiveStrain under the current objective regime.

    For each threshold metric, compute:
      - current_severity : how deep the violation is this year (0-1)
      - window_share     : fraction of recent window years in violation
    ObjectiveStrain = weighted average of (0.5*severity + 0.5*share) across metrics.
    Also computes LockInShare (fraction of window years under lock-in policies).
    """
    empty = {
        "ObjectiveStrain": 0.0,
        "LockInShare": 0.0,
        "DominantStrainMetric": "",
        "metric_severities": {},
        "metric_shares": {},
    }
    if not history_rows:
        return empty
    if lockin_policy_names is None:
        lockin_policy_names = _LOCKIN_POLICIES

    current  = history_rows[-1]
    recent   = history_rows[-window:] if len(history_rows) >= window else history_rows
    thresholds = regime_config.get("thresholds", [])
    if not thresholds:
        return empty

    total_weight = sum(float(t.get("weight", 1.0)) for t in thresholds)
    if total_weight <= 0:
        total_weight = 1.0

    metric_severities: Dict[str, float] = {}
    metric_shares:     Dict[str, float] = {}
    weighted_sum  = 0.0
    dominant_m    = ""
    max_sev       = -1.0

    for t in thresholds:
        metric = str(t.get("metric", "")).strip()
        if not metric:
            continue
        thr   = float(t.get("threshold", np.nan))
        direc = str(t.get("dir", "max")).strip().lower()
        w     = float(t.get("weight", 1.0)) / total_weight

        if not np.isfinite(thr):
            continue

        # Current-year violation severity
        v = float(current.get(metric, np.nan))
        if np.isfinite(v) and abs(thr) > 1e-12:
            raw_sev = (v - thr) / (abs(thr) + 1e-9) if direc == "max" else (thr - v) / (abs(thr) + 1e-9)
            sev = float(np.clip(raw_sev, 0.0, 1.0))
        else:
            sev = 0.0

        # Window violation share
        fail_c, total_c = 0, 0
        for row in recent:
            rv = float(row.get(metric, np.nan))
            if np.isfinite(rv):
                total_c += 1
                if (direc == "max" and rv > thr) or (direc == "min" and rv < thr):
                    fail_c += 1
        share = fail_c / max(1, total_c)

        combined = 0.5 * sev + 0.5 * share
        weighted_sum += combined * w
        metric_severities[metric] = sev
        metric_shares[metric]     = share

        if sev > max_sev:
            max_sev    = sev
            dominant_m = metric

    weighted_metric_strain = float(np.clip(weighted_sum, 0.0, 1.0))

    # Lock-in share (window)
    lock_c, pol_c = 0, 0
    for row in recent:
        p = str(row.get("PolicyApplied", row.get("Policy", "")))
        if p:
            pol_c += 1
            if p in lockin_policy_names:
                lock_c += 1
    lock_share = lock_c / max(1, pol_c)

    objective_strain = float(np.clip(
        (1.0 - lockin_weight) * weighted_metric_strain + lockin_weight * lock_share, 0.0, 1.0
    ))

    return {
        "ObjectiveStrain":      objective_strain,
        "LockInShare":          lock_share,
        "DominantStrainMetric": dominant_m,
        "metric_severities":    metric_severities,
        "metric_shares":        metric_shares,
    }


def _minmax_norm(values: List[float]) -> List[float]:
    arr = np.array(values, dtype=float)
    lo, hi = np.nanmin(arr), np.nanmax(arr)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-12:
        return [0.0] * len(values)
    return ((arr - lo) / (hi - lo)).tolist()


def _weighted_fail_ratio(
    df: pd.DataFrame,
    thresholds_list: List[dict],
    metric_priority: Optional[Dict[str, float]] = None,
) -> float:
    """Weighted violation severity ratio from a thresholds list (with 'weight' field)."""
    if df.empty or not thresholds_list:
        return 0.0
    if metric_priority is None:
        metric_priority = {}

    total_w = sum(float(t.get("weight", 1.0)) for t in thresholds_list) or 1.0
    numer, denom = 0.0, 0.0

    for t in thresholds_list:
        metric = str(t.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        thr   = float(t.get("threshold", np.nan))
        direc = str(t.get("dir", "max")).strip().lower()
        w     = float(t.get("weight", 1.0)) / total_w * float(metric_priority.get(metric, 1.0))
        if not np.isfinite(thr):
            continue
        vals = pd.to_numeric(df[metric], errors="coerce")
        valid = vals[np.isfinite(vals.values)]
        if valid.empty:
            continue
        if direc == "max":
            sev = ((valid - thr) / (abs(thr) + 1e-9)).clip(lower=0.0, upper=1.0)
        else:
            sev = ((thr - valid) / (abs(thr) + 1e-9)).clip(lower=0.0, upper=1.0)
        numer += float(sev.sum()) * w
        denom += float(len(valid)) * w

    return float(np.clip(numer / denom, 0.0, 1.0)) if denom > 1e-12 else 0.0


def _simulate_window_metrics(
    start_year: int,
    years: List[int],
    prev_values: dict,
    policy: dict,
    params: dict,
    thresholds_list: List[dict],
) -> Dict[str, float]:
    future = [int(y) for y in years if int(y) > int(start_year)]
    if not future:
        return {"fail_ratio": 0.0, "municipal_cost_npv": 0.0}
    sim_rows: List[dict] = []
    state = copy.deepcopy(prev_values)
    for yy in future:
        state, out = sim.simulate_year(int(yy), state, policy, params)
        out = out.to_dict() if isinstance(out, pd.Series) else dict(out)
        out["Year"] = int(yy)
        sim_rows.append(out)
    dfw = pd.DataFrame(sim_rows)
    fail_ratio = _weighted_fail_ratio(dfw, thresholds_list)
    mc_col  = pd.to_numeric(dfw.get("Municipal Cost", pd.Series(np.zeros(len(dfw)))), errors="coerce").fillna(0)
    mc_npv  = npv(mc_col.tolist(), dfw["Year"].astype(int).tolist(), 0.0)
    return {"fail_ratio": float(fail_ratio), "municipal_cost_npv": float(mc_npv)}


def _select_next_policy(
    decision_mode: str,
    current_policy_name: str,
    atp_metric: str,  # noqa: ARG001 – available for reactive trigger extension
    y: int,
    years: List[int],
    prev_values: dict,
    primitives: Dict[str, dict],
    params: dict,
    regime_config: dict,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    switch_penalty: float,
    ladder: Optional[List[str]] = None,
) -> str:
    """Choose next policy at Performance ATP (reactive or anticipatory)."""
    thresholds_list = regime_config.get("thresholds", [])

    if decision_mode.startswith("Reactive"):
        if ladder:
            try:
                idx = ladder.index(current_policy_name)
                return ladder[min(idx + 1, len(ladder) - 1)]
            except ValueError:
                return current_policy_name
        return current_policy_name

    # Anticipatory: evaluate all primitives over lookahead window
    candidates = list(primitives.keys())
    if not candidates:
        return current_policy_name

    years_win = [int(yy) for yy in years if int(yy) <= int(y) + int(lookahead_window_years)]
    rng_state = np.random.get_state()
    try:
        eval_rows = []
        for cand in candidates:
            m = _simulate_window_metrics(
                int(y), years_win, prev_values, primitives[cand], params, thresholds_list
            )
            is_switch = (cand != current_policy_name)
            eval_rows.append({
                "policy":            cand,
                "fail_ratio":        m["fail_ratio"],
                "municipal_cost_npv": m["municipal_cost_npv"] + float(switch_penalty) * is_switch,
                "is_switch":         is_switch,
            })
    finally:
        np.random.set_state(rng_state)

    fail_norm = _minmax_norm([r["fail_ratio"] for r in eval_rows])
    cost_norm = _minmax_norm([r["municipal_cost_npv"] for r in eval_rows])
    w_fail = float(lookahead_weights.get("fail_ratio", 0.6))
    w_cost = float(lookahead_weights.get("municipal_cost_npv", 0.4))
    wsum   = max(1e-12, w_fail + w_cost)
    w_fail /= wsum; w_cost /= wsum

    best, best_score = current_policy_name, np.inf
    for i, row in enumerate(eval_rows):
        score = w_fail * fail_norm[i] + w_cost * cost_norm[i]
        if score < best_score:
            best_score = score
            best = str(row["policy"])
    return best


def _select_next_regime(
    current_regime_name: str,
    candidate_names: List[str],
    all_regimes: Dict[str, dict],
    y: int,
    years: List[int],
    prev_values: dict,
    primitives: Dict[str, dict],
    params: dict,
    _current_policy_name: str,
    lookahead_window_years: int,
    discount_rate_local: float,
    switch_cost: float,  # noqa: ARG001 – reserved for future switch penalty term
) -> Tuple[str, Optional[str]]:
    """Select best next Objective Regime and suggested Policy by evaluating all primitives × candidates."""
    del _current_policy_name  # all primitives are evaluated; current policy is not privileged
    valid = [c for c in candidate_names if c in all_regimes]
    if not valid:
        return current_regime_name, None
    if len(valid) == 1:
        return valid[0], None

    future = [int(yy) for yy in years if int(yy) > int(y) and int(yy) <= int(y) + lookahead_window_years]
    if not future:
        return valid[0], None

    rng_state = np.random.get_state()
    try:
        best_score: float = float("inf")
        best_regime: str = valid[0]
        best_policy: Optional[str] = None

        for rname in valid:
            rcfg = all_regimes[rname]
            thr_list = rcfg.get("thresholds", [])
            for pname, policy in primitives.items():
                sim_rows: List[dict] = []
                state = copy.deepcopy(prev_values)
                for yy in future:
                    state, out = sim.simulate_year(int(yy), state, policy, params)
                    out = out.to_dict() if isinstance(out, pd.Series) else dict(out)
                    out["Year"] = int(yy)
                    sim_rows.append(out)
                dfw = pd.DataFrame(sim_rows)
                fail_r = _weighted_fail_ratio(dfw, thr_list)
                mc_col = pd.to_numeric(
                    dfw.get("Municipal Cost", pd.Series([0.0] * len(dfw))), errors="coerce"
                ).fillna(0.0)
                yrs_l  = dfw["Year"].astype(int).tolist() if "Year" in dfw.columns else future
                mc_npv_val = npv(mc_col.tolist(), yrs_l, discount_rate_local)
                mc_norm = mc_npv_val / (1e9 + abs(mc_npv_val))
                score = 0.6 * fail_r + 0.4 * mc_norm
                if score < best_score:
                    best_score  = score
                    best_regime = rname
                    best_policy = pname
    finally:
        np.random.set_state(rng_state)

    return best_regime, best_policy


# ========================== Representative Pathway Functions ==========================

def pathway_signature(
    df: pd.DataFrame,
    policy_col: str = "PolicyApplied",
    regime_col: str = "ObjectiveRegimeApplied",
) -> tuple:
    """
    Convert one scenario realization to a compact immutable sequence:
    ((start_year, end_year, regime, policy), ...)
    Consecutive years with the same regime+policy are merged.
    """
    if df.empty:
        return ()
    if policy_col not in df.columns and "Policy" in df.columns:
        policy_col = "Policy"
    if regime_col not in df.columns and "ObjectiveRegime" in df.columns:
        regime_col = "ObjectiveRegime"
    years    = df["Year"].astype(int).tolist()
    policies = df[policy_col].astype(str).tolist() if policy_col in df.columns else [""] * len(df)
    regimes  = df[regime_col].astype(str).tolist() if regime_col in df.columns else [""] * len(df)
    if not years:
        return ()

    segments = []
    sy, cp, cr = years[0], policies[0], regimes[0]
    for i in range(1, len(years)):
        if policies[i] != cp or regimes[i] != cr:
            segments.append((sy, years[i - 1], cr, cp))
            sy, cp, cr = years[i], policies[i], regimes[i]
    segments.append((sy, years[-1], cr, cp))
    return tuple(segments)


def pathway_switch_years(df: pd.DataFrame) -> List[int]:
    """Years when the applied regime/policy state changes."""
    sig = pathway_signature(df)
    return [int(seg[0]) for seg in sig[1:]]


def canonical_pathway_label(signature: tuple) -> str:
    """
    Return compact human-readable label, e.g.:
    'Agriculture-oriented/NoRegret-Lite → Safety-oriented/Relocation-Boost'
    """
    if not signature:
        return "(empty)"
    parts = [f"{reg}/{pol}" for _, _, reg, pol in signature]
    return " → ".join(parts)


def summarize_representative_pathways(
    series: List[pd.DataFrame],
    scorecard: pd.DataFrame,
    regime_switches: Optional[List[List[Tuple]]] = None,
    top_n: int = 8,
) -> pd.DataFrame:
    """
    Group scenario realizations by canonical pathway label.
    Returns table with occurrence share and mean performance metrics.
    """
    if not series:
        return pd.DataFrame()

    sigs   = [pathway_signature(df) for df in series]
    labels = [canonical_pathway_label(sig) for sig in sigs]
    regime_switches = regime_switches or [[] for _ in series]

    groups: Dict[str, List[int]] = {}
    for idx, label in enumerate(labels):
        groups.setdefault(label, []).append(idx)

    total = max(1, len(labels))
    rows  = []
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))

    for pid, (label, indices) in enumerate(sorted_groups[:top_n]):
        count = len(indices)
        share = count / total

        # Pull scorecard rows for this group
        sc_idx  = [i for i in indices if i < len(scorecard)]
        sc_sub  = scorecard.iloc[sc_idx] if sc_idx else pd.DataFrame()

        def _smean(col):
            if sc_sub.empty or col not in sc_sub.columns:
                return np.nan
            return float(sc_sub[col].mean())

        representative_scenario_id = int(indices[0]) if indices else -1

        sw_year_lists = [pathway_switch_years(series[i]) for i in indices if i < len(series)]
        max_sw_len = max((len(v) for v in sw_year_lists), default=0)
        med_switch_years: List[str] = []
        for pos in range(max_sw_len):
            vals = [yrs[pos] for yrs in sw_year_lists if len(yrs) > pos]
            if vals:
                med_switch_years.append(str(int(round(float(np.median(vals))))))

        objective_metrics: List[str] = []
        for i in indices:
            if i >= len(regime_switches):
                continue
            for sw in regime_switches[i]:
                if len(sw) >= 4 and str(sw[3]):
                    objective_metrics.append(str(sw[3]))

        performance_metrics: List[str] = []
        for df_i in [series[i] for i in indices if i < len(series)]:
            if "PerformanceATPMetric" in df_i.columns:
                performance_metrics.extend([
                    str(m) for m in df_i["PerformanceATPMetric"].dropna().astype(str).tolist()
                    if str(m) and str(m).lower() != "nan"
                ])

        def _metric_counts(values: List[str], max_items: int = 4) -> str:
            counts = Counter(v for v in values if v and v.lower() != "nan")
            return ", ".join(f"{m} ({c})" for m, c in counts.most_common(max_items))

        rows.append({
            "pathway_id":          pid + 1,
            "pathway_label":       label,
            "representative_scenario_id": representative_scenario_id,
            "n_segments":          len(sigs[indices[0]]) if indices else 0,
            "median_switch_years": ", ".join(med_switch_years),
            "objective_switch_metrics": _metric_counts(objective_metrics),
            "performance_trigger_metrics": _metric_counts(performance_metrics),
            "mean_InitialRegimeRobustness": _smean("Initial-regime Robustness"),
            "mean_RegimeAwareRobustness":   _smean("Regime-aware Robustness"),
            "mean_ObjectiveStrain":     _smean("Mean ObjectiveStrain"),
            "mean_LockIn_Years":        _smean("Lock-in Years"),
            "occurrence_count":    count,
            "occurrence_share":    share,
            "mean_NPV_Flood_Damage":    _smean("NPV Flood Damage"),
            "mean_NPV_Municipal_Cost":  _smean("NPV Municipal Cost"),
        })

    return pd.DataFrame(rows)


# ========================== build_pathway_generalized ==========================

def build_pathway_generalized(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    all_regimes: Dict[str, dict],
    initial_regime_name: str,
    objective_regime_mode: str,
    k_atp: int,
    cooldown_years: int,
    regime_switch_cost_val: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    policy_switch_penalty: float,
    strain_window: int,
    ladder: Optional[List[str]] = None,
    lockin_weight: float = 0.2,
) -> Tuple[pd.DataFrame, List[Tuple], List[Tuple], float]:
    """
    Single-scenario generalized pathway simulation.

    Returns
    -------
    df                     : per-year simulation DataFrame
    policy_switches        : [(year, atp_metric, new_policy), ...]
    objective_regime_switches : [(year, from_regime, to_regime, dominant_metric, strain_val), ...]
    total_switch_cost_npv  : float
    """
    if not all_regimes:
        raise ValueError("all_regimes is empty")
    if initial_regime_name not in all_regimes:
        raise ValueError(f"initial_regime '{initial_regime_name}' not in all_regimes")
    if not primitives:
        raise ValueError("primitives is empty")

    # Determine starting policy (first entry of ladder if available, else first primitive)
    if ladder and ladder[0] in primitives:
        current_policy_name = ladder[0]
    else:
        current_policy_name = next(iter(primitives))

    current_policy       = primitives[current_policy_name]
    current_regime_name  = initial_regime_name
    current_regime_cfg   = all_regimes[current_regime_name]

    prev_values          = dict(init)
    policy_switches:              List[Tuple] = []
    objective_regime_switches:    List[Tuple] = []
    out_rows:                     List[dict]  = []

    decision_start_year  = int(years[0]) if years else 0
    objective_atp_run    = 0
    cooldown_left        = 0
    y0                   = int(years[0]) if years else 0
    total_switch_cost    = 0.0

    for y in years:
        y = int(y)
        applied_policy_name = current_policy_name
        applied_policy = current_policy
        applied_regime_name = current_regime_name
        applied_regime_cfg = current_regime_cfg

        prev_values, outputs = sim.simulate_year(y, prev_values, applied_policy, params)
        outputs = outputs.to_dict() if isinstance(outputs, pd.Series) else dict(outputs)
        outputs["Year"] = y
        outputs["PolicyApplied"] = applied_policy_name
        outputs["ObjectiveRegimeApplied"] = applied_regime_name
        # Backward-compatible aliases. These mean "applied this year".
        outputs["Policy"] = applied_policy_name
        outputs["ObjectiveRegime"] = applied_regime_name

        policy_next = applied_policy_name
        regime_next = applied_regime_name
        suggested_policy_after_regime_switch = ""
        obj_atp_triggered = False
        regime_switch_reason = ""
        perf_atp_metric_out = ""
        policy_switch_recorded = False

        # ---- Compute ObjectiveStrain under the regime applied this year ----
        os_result = compute_objective_strain(
            out_rows + [outputs],
            applied_regime_cfg,
            lockin_policy_names=_LOCKIN_POLICIES,
            window=strain_window,
            lockin_weight=float(lockin_weight),
        )
        obj_strain = os_result["ObjectiveStrain"]
        dominant_m = os_result["DominantStrainMetric"]
        lock_share = os_result["LockInShare"]

        outputs["ObjectiveStrain"] = obj_strain
        outputs["DominantStrainMetric"] = dominant_m
        outputs["LockInShare"] = lock_share
        for _m, _sv in os_result.get("metric_severities", {}).items():
            outputs[f"StrainSeverity_{_m}"] = _sv
        for _m, _sh in os_result.get("metric_shares", {}).items():
            outputs[f"StrainShare_{_m}"] = _sh

        # ---- Objective ATP check (endogenous mode): decision recorded for next year ----
        if objective_regime_mode.startswith("Endogenous"):
            if cooldown_left <= 0:
                strain_thr = float(applied_regime_cfg.get("strain_threshold", 0.65))
                min_str_years = int(applied_regime_cfg.get("min_strain_years", 3))

                if obj_strain >= strain_thr:
                    objective_atp_run += 1
                else:
                    objective_atp_run = 0

                if objective_atp_run >= min_str_years:
                    candidates = applied_regime_cfg.get("next_regime_candidates", [])
                    new_regime, suggested_policy = _select_next_regime(
                        applied_regime_name, candidates, all_regimes,
                        y, years, prev_values, primitives, params,
                        applied_policy_name, lookahead_window_years,
                        discount_rate_local, regime_switch_cost_val,
                    )
                    obj_atp_triggered = True
                    objective_atp_run = 0
                    if suggested_policy:
                        suggested_policy_after_regime_switch = str(suggested_policy)

                    base_reason = (
                        f"ObjectiveStrain={obj_strain:.3f}>={strain_thr:.2f} "
                        f"for {min_str_years} yrs; dominant={dominant_m}"
                    )
                    if new_regime != applied_regime_name:
                        objective_regime_switches.append(
                            (y, applied_regime_name, new_regime, dominant_m, obj_strain)
                        )
                        total_switch_cost += float(regime_switch_cost_val) / (
                            (1 + float(discount_rate_local)) ** (y - y0)
                        )
                        regime_next = new_regime
                        regime_switch_reason = f"{base_reason}; next={new_regime}"
                        cooldown_left = int(cooldown_years)
                        decision_start_year = y + 1

                        if suggested_policy and suggested_policy in primitives and suggested_policy != applied_policy_name:
                            policy_next = str(suggested_policy)
                            policy_switches.append((y, "ObjectiveRegimeSwitch", policy_next))
                            policy_switch_recorded = True
                    else:
                        regime_switch_reason = f"{base_reason}; no regime change selected"
            else:
                cooldown_left -= 1

        # ---- Performance ATP check under the regime applied this year ----
        df_so_far = pd.DataFrame(out_rows + [outputs])
        df_seg = df_so_far[df_so_far["Year"].astype(int) >= int(decision_start_year)].copy()
        thr_df = _regime_thresholds_df(applied_regime_cfg)

        atp = detect_atp_earliest(df_seg, thr_df, int(k_atp))
        if atp is not None:
            atp_year, atp_metric = atp
            if y == int(atp_year) + int(k_atp) - 1:
                perf_atp_metric_out = str(atp_metric)
                if not policy_switch_recorded:
                    new_pol = _select_next_policy(
                        decision_mode=decision_mode,
                        current_policy_name=applied_policy_name,
                        atp_metric=str(atp_metric),
                        y=y,
                        years=years,
                        prev_values=prev_values,
                        primitives=primitives,
                        params=params,
                        regime_config=applied_regime_cfg,
                        lookahead_window_years=int(lookahead_window_years),
                        lookahead_weights=lookahead_weights,
                        switch_penalty=float(policy_switch_penalty),
                        ladder=ladder,
                    )
                    if new_pol != applied_policy_name:
                        policy_next = str(new_pol)
                        policy_switches.append((y, str(atp_metric), policy_next))
                        decision_start_year = y + 1

        outputs["PolicyNext"] = policy_next
        outputs["ObjectiveRegimeNext"] = regime_next
        outputs["ObjectiveATPTriggered"] = obj_atp_triggered
        outputs["PerformanceATPMetric"] = perf_atp_metric_out
        outputs["ObjectiveRegimeSwitchReason"] = regime_switch_reason
        outputs["SuggestedPolicyAfterRegimeSwitch"] = suggested_policy_after_regime_switch

        out_rows.append(outputs)

        # Decisions made in year y become the applied state at the start of year y+1.
        current_policy_name = policy_next if policy_next in primitives else applied_policy_name
        current_policy = primitives[current_policy_name]
        current_regime_name = regime_next if regime_next in all_regimes else applied_regime_name
        current_regime_cfg = all_regimes[current_regime_name]

    return pd.DataFrame(out_rows), policy_switches, objective_regime_switches, float(total_switch_cost)


def run_mc_generalized(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    all_regimes: Dict[str, dict],
    initial_regime_name: str,
    objective_regime_mode: str,
    k_atp: int,
    n: int,
    cooldown_years: int,
    regime_switch_cost_val: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    policy_switch_penalty: float,
    strain_window: int,
    ladder: Optional[List[str]],
    lockin_weight: float,
    rng: np.random.Generator,
) -> Tuple[List[pd.DataFrame], List[List], List[List], List[float], List[int]]:
    series, pol_sw, reg_sw, costs, seeds = [], [], [], [], []
    for _ in range(int(n)):
        seed_i = int(rng.integers(0, 2**32 - 1))
        seeds.append(seed_i)
        np.random.seed(seed_i)
        df_i, psw_i, rsw_i, cost_i = build_pathway_generalized(
            years, init, primitives, params,
            all_regimes, initial_regime_name, objective_regime_mode,
            k_atp, cooldown_years, regime_switch_cost_val, discount_rate_local,
            decision_mode, lookahead_window_years, lookahead_weights,
            policy_switch_penalty, strain_window, ladder, lockin_weight,
        )
        series.append(df_i)
        pol_sw.append(psw_i)
        reg_sw.append(rsw_i)
        costs.append(cost_i)
    return series, pol_sw, reg_sw, costs, seeds


def run_mc_generalized_with_seeds(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params: dict,
    all_regimes: Dict[str, dict],
    initial_regime_name: str,
    objective_regime_mode: str,
    k_atp: int,
    scenario_seeds: List[int],
    cooldown_years: int,
    regime_switch_cost_val: float,
    discount_rate_local: float,
    decision_mode: str,
    lookahead_window_years: int,
    lookahead_weights: Dict[str, float],
    policy_switch_penalty: float,
    strain_window: int,
    ladder: Optional[List[str]],
    lockin_weight: float,
) -> Tuple[List[pd.DataFrame], List[List], List[List], List[float]]:
    series, pol_sw, reg_sw, costs = [], [], [], []
    for seed_i in scenario_seeds:
        np.random.seed(int(seed_i) & 0xFFFFFFFF)
        df_i, psw_i, rsw_i, cost_i = build_pathway_generalized(
            years, init, primitives, params,
            all_regimes, initial_regime_name, objective_regime_mode,
            k_atp, cooldown_years, regime_switch_cost_val, discount_rate_local,
            decision_mode, lookahead_window_years, lookahead_weights,
            policy_switch_penalty, strain_window, ladder, lockin_weight,
        )
        series.append(df_i)
        pol_sw.append(psw_i)
        reg_sw.append(rsw_i)
        costs.append(cost_i)
    return series, pol_sw, reg_sw, costs


# ========================== Scorecard Helpers ==========================

def _get_value_at_year(df: pd.DataFrame, metric: str, year: int) -> float:
    if metric not in df.columns:
        return np.nan
    row = df[df["Year"].astype(int) == year]
    return float(row[metric].iloc[0]) if not row.empty else np.nan


def _row_meets_thresholds(row: pd.Series, thresholds_list: List[dict]) -> bool:
    for t in thresholds_list:
        metric = str(t.get("metric", "")).strip()
        if not metric or metric not in row.index:
            continue
        thr = float(t.get("threshold", np.nan))
        direc = str(t.get("dir", "max")).strip().lower()
        val = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
        if not np.isfinite(val) or not np.isfinite(thr):
            continue
        if direc == "max" and not (val <= thr):
            return False
        if direc == "min" and not (val >= thr):
            return False
    return True


def _robustness_against_thresholds(df: pd.DataFrame, thresholds_list: List[dict]) -> float:
    if df.empty:
        return np.nan
    meets = [_row_meets_thresholds(row, thresholds_list) for _, row in df.iterrows()]
    return float(np.mean(meets)) if meets else np.nan


def _regime_aware_robustness(
    df: pd.DataFrame,
    all_regimes: Optional[Dict[str, dict]],
    fallback_regime_config: dict,
) -> float:
    if df.empty:
        return np.nan
    all_regimes = all_regimes or {}
    regime_col = "ObjectiveRegimeApplied" if "ObjectiveRegimeApplied" in df.columns else "ObjectiveRegime"
    meets: List[bool] = []
    for _, row in df.iterrows():
        rname = str(row.get(regime_col, ""))
        rcfg = all_regimes.get(rname, fallback_regime_config)
        meets.append(_row_meets_thresholds(row, rcfg.get("thresholds", [])))
    return float(np.mean(meets)) if meets else np.nan


def summarize_df(
    df: pd.DataFrame,
    eval_regime_config: dict,
    discount_rate_local: float,
    all_regimes: Optional[Dict[str, dict]] = None,
) -> dict:
    """Summarize a single scenario DataFrame against the given regime's thresholds."""
    thresholds_list = eval_regime_config.get("thresholds", [])
    thr_df = pd.DataFrame([
        {"metric": t["metric"], "threshold": float(t["threshold"]), "dir": t["dir"]}
        for t in thresholds_list if t.get("metric")
    ])

    # Initial-regime robustness: all years evaluated by the initial regime thresholds.
    initial_regime_robustness = _robustness_against_thresholds(df, thresholds_list)
    regime_aware_robustness = _regime_aware_robustness(df, all_regimes, eval_regime_config)

    years = df["Year"].astype(int).tolist() if "Year" in df.columns else list(range(len(df)))
    mc_col = pd.to_numeric(df.get("Municipal Cost", pd.Series(np.zeros(len(df)))), errors="coerce").fillna(0)
    fd_col = pd.to_numeric(df.get("Flood Damage",   pd.Series(np.zeros(len(df)))), errors="coerce").fillna(0)
    npv_cost   = npv(mc_col.tolist(), years, discount_rate_local)
    npv_damage = npv(fd_col.tolist(), years, discount_rate_local)

    policy_col_name = "PolicyApplied" if "PolicyApplied" in df.columns else "Policy"
    policy_col = df.get(policy_col_name, pd.Series([""] * len(df))).astype(str)

    # Lock-in years (AgriR&D / All-Boost)
    lock_in_years = int(policy_col.isin(_LOCKIN_POLICIES).sum())

    # Early window (first 20 years)
    y_start = int(df["Year"].min()) if "Year" in df.columns else 0
    early_mask = df["Year"].astype(int) < y_start + 20
    early_pol  = policy_col[early_mask]
    early_mc   = mc_col[early_mask]
    n_early    = max(1, len(early_pol))
    early_irrev_mask  = early_pol.isin(_IRREVERSIBLE_POLICIES).values
    early_irrev_years = int(early_irrev_mask.sum())
    early_irrev_cost  = float(early_mc.values[early_irrev_mask].sum()) if early_irrev_mask.any() else 0.0
    early_opt_share   = float(early_pol.isin(_FLEXIBLE_POLICIES).sum()) / n_early

    # ObjectiveStrain
    if "ObjectiveStrain" in df.columns:
        os_vals = pd.to_numeric(df["ObjectiveStrain"], errors="coerce").dropna()
        mean_os = float(os_vals.mean()) if len(os_vals) > 0 else np.nan
        max_os  = float(os_vals.max())  if len(os_vals) > 0 else np.nan
    else:
        mean_os = max_os = np.nan

    # Time-point metrics
    def _tp(metric, year):
        return _get_value_at_year(df, metric, year)

    return {
        "Initial-regime Robustness":           initial_regime_robustness,
        "Regime-aware Robustness":             regime_aware_robustness,
        "Robustness":                          initial_regime_robustness,
        "NPV Municipal Cost":                  npv_cost,
        "NPV Flood Damage":                    npv_damage,
        "Avg Resident Burden":                 float(df.get("Resident Burden", pd.Series([np.nan])).mean()),
        "Min Ecosystem Level":                 float(df.get("Ecosystem Level", pd.Series([np.nan])).min()),
        "Avg Crop Yield":                      float(df.get("Crop Yield", pd.Series([np.nan])).mean()),
        "Final Levee Level":                   float(df.get("Levee Level", pd.Series([np.nan])).iloc[-1]) if "Levee Level" in df.columns else np.nan,
        "Flood Damage 2050":   _tp("Flood Damage", 2050),
        "Flood Damage 2100":   _tp("Flood Damage", 2100),
        "Resident Burden 2050": _tp("Resident Burden", 2050),
        "Resident Burden 2100": _tp("Resident Burden", 2100),
        "Ecosystem Level 2050": _tp("Ecosystem Level", 2050),
        "Ecosystem Level 2100": _tp("Ecosystem Level", 2100),
        "Crop Yield 2050":     _tp("Crop Yield", 2050),
        "Crop Yield 2100":     _tp("Crop Yield", 2100),
        "Lock-in Years":                       lock_in_years,
        "Early Irreversible Commitment Years": early_irrev_years,
        "Early Irreversible Commitment Cost":  early_irrev_cost,
        "Option-preserving Share Early":       early_opt_share,
        "Mean ObjectiveStrain":                mean_os,
        "Max ObjectiveStrain":                 max_os,
        "Cumulative Municipal Cost":           float(mc_col.sum()),
    }


# ========================== Run Button ==========================
st.divider()
run_clicked = st.button("▶️ Run DAPP (Monte Carlo)", key="run_btn")

if run_clicked:
    rng = np.random.default_rng(int(base_seed)) if use_fixed_seed else np.random.default_rng()

    with st.status("Running Monte Carlo...", expanded=True) as status:
        status.update(label=f"Simulating with initial regime: {initial_regime}")

        _lw = {"fail_ratio": float(lookahead_w_fail), "municipal_cost_npv": float(lookahead_w_cost)}

        series, policy_switches, regime_switches, npv_costs, scenario_seeds = run_mc_generalized(
            YEARS, DEFAULT_INITIAL, PRIMITIVE_POLICIES, params,
            OBJECTIVE_REGIMES, initial_regime, objective_regime_mode,
            int(k_consec), int(n_scenarios),
            int(cooldown_years), float(regime_switch_cost),
            float(discount_rate), decision_mode,
            int(lookahead_window_years), _lw, float(policy_switch_cost),
            int(strain_window_years), ladder_global, float(lockin_weight), rng,
        )

        status.update(label="Building scorecards...")
        eval_regime_cfg = OBJECTIVE_REGIMES.get(initial_regime, next(iter(OBJECTIVE_REGIMES.values())))

        sc_rows = []
        for i, df in enumerate(series):
            s = summarize_df(df, eval_regime_cfg, float(discount_rate), OBJECTIVE_REGIMES)
            psw = policy_switches[i] if i < len(policy_switches) else []
            rsw = regime_switches[i]  if i < len(regime_switches)  else []

            s["#PolicySwitches"]        = len(psw)
            s["#ObjectiveRegimeSwitches"] = len(rsw)
            s["ObjectiveRegimeSwitchYear"] = rsw[0][0] if rsw else np.nan
            s["NPV RegimeSwitchCost"]   = float(npv_costs[i]) if i < len(npv_costs) else 0.0

            mc_col_i = pd.to_numeric(
                df.get("Municipal Cost", pd.Series(np.zeros(len(df)))), errors="coerce"
            ).fillna(0.0)
            _pol_col_i_name = "PolicyApplied" if "PolicyApplied" in df.columns else "Policy"
            pol_col_i = df.get(_pol_col_i_name, pd.Series([""] * len(df))).astype(str)
            s["Cumulative PolicySwitch Cost"] = float(len(psw) * float(policy_switch_cost))
            s["Cumulative RegimeSwitch Cost"] = float(len(rsw) * float(regime_switch_cost))
            s["Cumulative Switching Cost"]    = float(s["Cumulative PolicySwitch Cost"] + s["Cumulative RegimeSwitch Cost"])
            s["Cumulative Total Cost"]        = float(s["Cumulative Municipal Cost"] + s["Cumulative Switching Cost"])
            for pnm in sorted(PRIMITIVE_POLICIES.keys()):
                s[f"MC [{pnm}]"] = float(mc_col_i[pol_col_i == pnm].sum())
            sc_rows.append(s)

        scorecard = pd.DataFrame(sc_rows)
        _num_cols = scorecard.select_dtypes(include=np.number).columns.tolist()
        cand_mean = scorecard[_num_cols].mean(numeric_only=True).rename(lambda c: c + " (mean)")
        cand_std  = scorecard[_num_cols].std(numeric_only=True).rename(lambda c: c + " (std)")
        cand_agg  = pd.concat([cand_mean, cand_std]).to_frame("Value").reset_index().rename(columns={"index": "Metric"})

        status.update(label="Extracting representative pathways...")
        rep_pathways = summarize_representative_pathways(series, scorecard, regime_switches, top_n=8)

        st.session_state["dapp_results"] = {
            "series":            series,
            "policy_switches":   policy_switches,
            "regime_switches":   regime_switches,
            "npv_costs":         npv_costs,
            "scorecard":         scorecard,
            "cand_agg":          cand_agg,
            "rep_pathways":      rep_pathways,
            "eval_regime_cfg":   eval_regime_cfg,
            "all_regimes":       OBJECTIVE_REGIMES,
            "initial_regime":    initial_regime,
            "objective_regime_mode": objective_regime_mode,
            "years":             YEARS,
            "k_consec":          int(k_consec),
            "decision_mode":     decision_mode,
            "lookahead_window":  int(lookahead_window_years),
            "lookahead_weights": _lw,
            "policy_switch_cost":    float(policy_switch_cost),
            "regime_switch_cost":    float(regime_switch_cost),
            "discount_rate":     float(discount_rate),
            "n_scenarios":       int(n_scenarios),
            "params":            params,
            "scenario_seeds":    list(scenario_seeds),
            "strain_window":     int(strain_window_years),
            "lockin_weight":     float(lockin_weight),
            "cooldown_years":    int(cooldown_years),
            "ladder":            ladder_global,
            "primitives":        PRIMITIVE_POLICIES,
            "seed":              int(base_seed) if use_fixed_seed else None,
        }
        status.update(label="Done.", state="complete")

# ========================== Results ==========================
st.divider()
st.header("Results (persisted)")

if "dapp_results" not in st.session_state:
    st.info("Click **Run DAPP (Monte Carlo)** to compute results.")
    st.stop()

res = st.session_state["dapp_results"]
seed_txt = f"seed={res.get('seed')}" if res.get("seed") is not None else "seed=(random)"
st.caption(
    f"Last run: {res['n_scenarios']} scenarios · {seed_txt} · "
    f"initial regime={res['initial_regime']} · mode={res['objective_regime_mode']}"
)

scorecard    = pd.DataFrame(res["scorecard"])
series       = res["series"]
rep_pathways = pd.DataFrame(res.get("rep_pathways", pd.DataFrame()))

base_colorway     = list(pq.Plotly)
years_sorted      = sorted({int(y) for df in series for y in df["Year"].unique()})

def _series_text_col(df: pd.DataFrame, primary: str, fallback: str) -> pd.Series:
    if primary in df.columns:
        return df[primary].astype(str)
    if fallback in df.columns:
        return df[fallback].astype(str)
    return pd.Series([""] * len(df), dtype=str)


policy_names      = sorted({p for df in series for p in _series_text_col(df, "PolicyApplied", "Policy").unique()})
regime_names_res  = sorted({r for df in series for r in _series_text_col(df, "ObjectiveRegimeApplied", "ObjectiveRegime").unique()})
policy_color_map  = {p: base_colorway[i % len(base_colorway)] for i, p in enumerate(policy_names)}
regime_color_map  = {r: base_colorway[i % len(base_colorway)] for i, r in enumerate(regime_names_res)}

# ---- A) Adaptive Rule Summary ----
st.subheader("A) Adaptive Rule Summary")
a_col1, a_col2, a_col3, a_col4 = st.columns(4)
a_col1.metric("Initial Objective Regime", res["initial_regime"])
a_col2.metric("Objective Regime Mode",    res["objective_regime_mode"].split("(")[0].strip())
a_col3.metric("Policy Decision Mode",     res["decision_mode"].split(":")[0].strip())
a_col4.metric("Lookahead Window",         f"{res['lookahead_window']} yrs")

b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
b_col1.metric("Policy Primitives",  len(res["primitives"]))
b_col2.metric("Objective Regimes",  len(res["all_regimes"]))
b_col3.metric("Performance ATP k",  res["k_consec"])
b_col4.metric("Scenarios",          res["n_scenarios"])
b_col5.metric("Lock-in Weight",      f"{float(res.get('lockin_weight', 0.2)):.2f}")

with st.expander("Objective Regime configurations used"):
    for rname, rcfg in res["all_regimes"].items():
        st.markdown(f"**{rname}**: {rcfg.get('description','')}")
        st.dataframe(
            pd.DataFrame(rcfg.get("thresholds", [])),
            use_container_width=True, hide_index=True
        )
        st.caption(
            f"strain_threshold={rcfg.get('strain_threshold', 0.65):.2f}  "
            f"min_strain_years={rcfg.get('min_strain_years', 3)}  "
            f"next_candidates={rcfg.get('next_regime_candidates', [])}"
        )

# ---- B) Representative Realized Pathways ----
st.subheader("B) Representative Realized Pathways")
st.caption(
    "Percentages are **occurrence shares of realized pathways under the adaptive rule** "
    "across Monte Carlo scenarios — not the probability of the pathway itself."
)

if rep_pathways.empty:
    st.info("No pathways extracted.")
else:
    top_n_show = st.slider("Show top N pathways", 1, min(8, len(rep_pathways)), min(5, len(rep_pathways)), 1, key="top_n_show")
    rp_display = rep_pathways.head(top_n_show).copy()
    displayed_share_sum = float(pd.to_numeric(rp_display["occurrence_share"], errors="coerce").sum())
    rp_display["occurrence_share"] = rp_display["occurrence_share"].map("{:.1%}".format)
    st.dataframe(rp_display, use_container_width=True, hide_index=True)
    st.caption(f"Displayed top {top_n_show} pathways account for {displayed_share_sum:.1%} of scenarios.")

    # Mini metro map for selected pathway
    if not rep_pathways.empty and len(series) > 0:
        sel_label = st.selectbox(
            "Select a representative pathway to visualize",
            options=rep_pathways["pathway_label"].tolist(),
            key="sel_pathway_label",
        )
        # Find one scenario matching that label
        sigs   = [pathway_signature(df) for df in series]
        labels = [canonical_pathway_label(sig) for sig in sigs]
        match_idx = next((i for i, l in enumerate(labels) if l == sel_label), None)

        if match_idx is not None:
            df_rep = series[match_idx]
            fig_rep = go.Figure()
            reg_col_rep = _series_text_col(df_rep, "ObjectiveRegimeApplied", "ObjectiveRegime")
            pol_col_rep = _series_text_col(df_rep, "PolicyApplied",          "Policy")
            yr_rep      = df_rep["Year"].astype(int).tolist()

            # Shade regimes as background
            _prev_r, _py0 = reg_col_rep.iloc[0], yr_rep[0]
            _regime_bands = []
            for _i in range(1, len(yr_rep)):
                if reg_col_rep.iloc[_i] != _prev_r or _i == len(yr_rep) - 1:
                    _regime_bands.append((_py0, yr_rep[_i - 1], _prev_r))
                    _py0, _prev_r = yr_rep[_i], reg_col_rep.iloc[_i]
            _regime_bands.append((_py0, yr_rep[-1], _prev_r))

            _pol_y_map = {p: j for j, p in enumerate(sorted(set(pol_col_rep.tolist())))}
            for _rb_start, _rb_end, _rb_reg in _regime_bands:
                fig_rep.add_vrect(
                    x0=_rb_start, x1=_rb_end + 1,
                    fillcolor=regime_color_map.get(_rb_reg, "lightgray"),
                    opacity=0.18, layer="below", line_width=0,
                    annotation_text=_rb_reg, annotation_position="top left",
                )

            fig_rep.add_trace(go.Scatter(
                x=yr_rep,
                y=[_pol_y_map[p] for p in pol_col_rep],
                mode="lines+markers",
                line=dict(width=2, color="black"),
                marker=dict(
                    size=8,
                    color=[policy_color_map.get(p, "gray") for p in pol_col_rep],
                ),
                text=[f"{y}: {r}/{p}" for y, r, p in zip(yr_rep, reg_col_rep, pol_col_rep)],
                hoverinfo="text",
                name="Pathway",
            ))
            _pol_labels = sorted(set(pol_col_rep.tolist()), key=lambda x: _pol_y_map[x])
            fig_rep.update_layout(
                title=f"Representative pathway (one scenario): {sel_label[:60]}",
                xaxis_title="Year",
                yaxis=dict(tickmode="array", tickvals=list(_pol_y_map.values()), ticktext=_pol_labels),
                height=380,
            )
            st.plotly_chart(fig_rep, use_container_width=True, key=f"rep_path_{render_uid}")
            occur_row = rep_pathways[rep_pathways["pathway_label"] == sel_label]
            if not occur_row.empty:
                occ_n     = int(occur_row["occurrence_count"].iloc[0])
                occ_share = float(occur_row["occurrence_share"].iloc[0])
                st.caption(
                    f"This pathway occurred in **{occ_n}/{res['n_scenarios']} scenarios "
                    f"({occ_share:.1%})** — occurrence share under the adaptive rule."
                )

# ---- C) Objective Regime Composition ----
st.subheader("C) Objective Regime Composition over time")
if regime_names_res:
    data_r = {r: [] for r in regime_names_res}
    for y in years_sorted:
        total = max(1, len(series))
        per_r: Dict[str, int] = {r: 0 for r in regime_names_res}
        for df in series:
            row = df[df["Year"] == y]
            regime_col_y = "ObjectiveRegimeApplied" if "ObjectiveRegimeApplied" in row.columns else "ObjectiveRegime"
            if not row.empty and regime_col_y in row.columns:
                rn = str(row[regime_col_y].iloc[0])
                per_r[rn] = per_r.get(rn, 0) + 1
        for rn in regime_names_res:
            data_r[rn].append(per_r[rn] / total)

    fig_r = go.Figure()
    for rn in regime_names_res:
        fig_r.add_trace(go.Scatter(
            x=years_sorted, y=data_r[rn],
            mode="lines", stackgroup="one", name=rn,
            line=dict(color=regime_color_map.get(rn)),
        ))
    fig_r.update_layout(
        title="ObjectiveRegimeApplied share across scenarios",
        xaxis_title="Year", yaxis_title="Share",
    )
    st.plotly_chart(fig_r, use_container_width=True, key=f"regime_share_{render_uid}")

    # Regime switch distribution
    all_rsw = res.get("regime_switches", [])
    switch_years_all = [int(e[0]) for sw in all_rsw for e in sw]
    if switch_years_all:
        n_shifted = sum(1 for sw in all_rsw if sw)
        st.caption(
            f"Objective Regime switches: {n_shifted}/{res['n_scenarios']} scenarios "
            f"({100*n_shifted/max(1,res['n_scenarios']):.1f}%)  |  "
            f"Mean switch year: {np.mean(switch_years_all):.1f}"
        )
        fig_rsw = go.Figure()
        fig_rsw.add_trace(go.Histogram(
            x=switch_years_all, nbinsx=max(1, len(years_sorted) // 5),
            marker_color="firebrick", opacity=0.75, name="Regime switch year",
        ))
        fig_rsw.update_layout(
            title="Distribution of Objective Regime switch years",
            xaxis_title="Year", yaxis_title="Count",
        )
        st.plotly_chart(fig_rsw, use_container_width=True, key=f"rsw_hist_{render_uid}")
else:
    st.info("No Objective Regime column found.")

# ---- D) Policy Composition ----
st.subheader("D) Policy Composition over time")
data_p = {p: [] for p in policy_names}
for y in years_sorted:
    total = max(1, len(series))
    per_p: Dict[str, int] = {p: 0 for p in policy_names}
    for df in series:
        row = df[df["Year"] == y]
        policy_col_y = "PolicyApplied" if "PolicyApplied" in row.columns else "Policy"
        if not row.empty and policy_col_y in row.columns:
            pn = str(row[policy_col_y].iloc[0])
            per_p[pn] = per_p.get(pn, 0) + 1
    for pn in policy_names:
        data_p[pn].append(per_p[pn] / total)

fig_p = go.Figure()
for pn in policy_names:
    fig_p.add_trace(go.Scatter(
        x=years_sorted, y=data_p[pn],
        mode="lines", stackgroup="one", name=pn,
        line=dict(color=policy_color_map.get(pn)),
    ))
fig_p.update_layout(
    title="PolicyApplied share across scenarios",
    xaxis_title="Year", yaxis_title="Share",
)
st.plotly_chart(fig_p, use_container_width=True, key=f"policy_share_{render_uid}")

# ---- E) Metro Map ----
st.subheader("E) Metro Map (time × policy × objective regime)")
bin_size_metro = st.slider("Time bucket (years)", 5, 25, 10, step=1, key="metro_bin")

all_pol_metro    = policy_names
all_regime_metro = regime_names_res
combined_states  = sorted({
    (r, p)
    for df in series
    for r, p in zip(
        _series_text_col(df, "ObjectiveRegimeApplied", "ObjectiveRegime"),
        _series_text_col(df, "PolicyApplied",          "Policy"),
    )
})
cs_idx = {cs: i for i, cs in enumerate(combined_states)}
cs_colors = {
    (r, p): regime_color_map.get(r, base_colorway[0])
    for r, p in combined_states
}

if years_sorted:
    sy_m, ey_m = min(years_sorted), max(years_sorted)
    buckets_m  = list(range(sy_m, ey_m + 1, int(bin_size_metro)))
    if buckets_m[-1] != ey_m:
        buckets_m.append(ey_m)

    nodes_m: Dict[Tuple, int] = {(b, cs): 0 for b in buckets_m for cs in combined_states}
    edges_m: Dict[Tuple, int] = {
        ((buckets_m[i], a), (buckets_m[i + 1], b)): 0
        for i in range(len(buckets_m) - 1)
        for a in combined_states
        for b in combined_states
    }

    for df in series:
        _pol_col_m = "PolicyApplied" if "PolicyApplied" in df.columns else "Policy"
        _reg_col_m = "ObjectiveRegimeApplied" if "ObjectiveRegimeApplied" in df.columns else "ObjectiveRegime"
        if _pol_col_m not in df.columns or _reg_col_m not in df.columns:
            continue
        df_l = df[["Year", _pol_col_m, _reg_col_m]].copy()
        df_l = df_l.rename(columns={_pol_col_m: "Policy", _reg_col_m: "ObjectiveRegime"})
        df_l["Year"] = df_l["Year"].astype(int)
        bucket_cs: Dict[int, Tuple] = {}

        for _bi, b0 in enumerate(buckets_m[:-1]):
            b1   = buckets_m[_bi + 1]
            mask = (df_l["Year"] >= b0) & (df_l["Year"] < b1)
            sub  = df_l[mask]
            if sub.empty:
                continue
            mode_r = sub["ObjectiveRegime"].mode().iloc[0]
            mode_p = sub["Policy"].mode().iloc[0]
            cs_val = (str(mode_r), str(mode_p))
            bucket_cs[b0] = cs_val
            if cs_val in cs_idx:
                nodes_m[(b0, cs_val)] += 1

        last_b = buckets_m[-1]
        sub_last = df_l[df_l["Year"] >= last_b]
        if not sub_last.empty:
            mode_r = sub_last["ObjectiveRegime"].mode().iloc[0]
            mode_p = sub_last["Policy"].mode().iloc[0]
            cs_last = (str(mode_r), str(mode_p))
            bucket_cs[last_b] = cs_last
            if cs_last in cs_idx:
                nodes_m[(last_b, cs_last)] += 1

        for _bi in range(len(buckets_m) - 1):
            b0, b1 = buckets_m[_bi], buckets_m[_bi + 1]
            if b0 in bucket_cs and b1 in bucket_cs:
                edges_m[((b0, bucket_cs[b0]), (b1, bucket_cs[b1]))] = \
                    edges_m.get(((b0, bucket_cs[b0]), (b1, bucket_cs[b1])), 0) + 1

    n_sc = max(1, len(series))
    node_share_m = {k: v / n_sc for k, v in nodes_m.items()}
    edge_share_m = {k: v / n_sc for k, v in edges_m.items() if v > 0}

    figm = go.Figure()
    for ((b0, a_cs), (b1, b_cs)), sh in edge_share_m.items():
        x0, y0_ = b0, cs_idx.get(a_cs, 0)
        x1, y1_ = b1, cs_idx.get(b_cs, 0)
        lw = max(1.0, 16 * sh)
        clr = cs_colors.get(a_cs, "rgba(80,80,80,0.55)") if a_cs == b_cs else "rgba(80,80,80,0.55)"
        figm.add_trace(go.Scatter(
            x=[x0, x1], y=[y0_, y1_], mode="lines",
            line=dict(width=lw, color=clr),
            hovertext=[f"{a_cs[0]}/{a_cs[1]} → {b_cs[0]}/{b_cs[1]}  sh={sh:.2f}"] * 2,
            hoverinfo="text", showlegend=False,
        ))

    nx_m, ny_m, ns_m, nt_m, nc_m = [], [], [], [], []
    for (b, cs), sh in node_share_m.items():
        if sh <= 0:
            continue
        nx_m.append(b)
        ny_m.append(cs_idx.get(cs, 0))
        ns_m.append(max(7, 38 * sh ** 0.5))
        nt_m.append(f"{sh * 100:.0f}%")
        nc_m.append(cs_colors.get(cs, base_colorway[0]))

    figm.add_trace(go.Scatter(
        x=nx_m, y=ny_m, mode="markers+text",
        marker=dict(size=ns_m, color=nc_m, line=dict(color="white", width=0.8)),
        text=nt_m, textposition="top center",
        hovertext=[f"{combined_states[ny_m[i]][0]}/{combined_states[ny_m[i]][1]}" for i in range(len(nx_m))],
        hoverinfo="text", showlegend=False,
    ))

    cs_labels = [f"{r}/{p}" for r, p in combined_states]
    figm.update_layout(
        title="Metro map (ObjectiveRegimeApplied / PolicyApplied)",
        xaxis_title="Year",
        yaxis=dict(tickmode="array", tickvals=list(range(len(combined_states))), ticktext=cs_labels),
        xaxis=dict(range=[sy_m - bin_size_metro * 0.5, ey_m + bin_size_metro * 0.5]),
        height=max(420, 60 * len(combined_states)),
    )
    st.plotly_chart(figm, use_container_width=True, key=f"metro_{render_uid}_{bin_size_metro}")

# ---- F) Scorecards ----
st.subheader("F) Scorecards")
st.caption(
    f"Initial-regime Robustness evaluates all years against **{res['initial_regime']}**; "
    "Regime-aware Robustness evaluates each year against ObjectiveRegimeApplied."
)

with st.expander("F1) Per-scenario scorecards"):
    st.dataframe(scorecard, use_container_width=True)

with st.expander("F2) Aggregate statistics (mean / std)"):
    st.dataframe(pd.DataFrame(res["cand_agg"]), use_container_width=True)

# Key metrics summary
e_col = st.columns(6)
def _sc_mean(col):
    if col in scorecard.columns:
        return float(scorecard[col].mean())
    return np.nan

e_col[0].metric("Initial-regime Robustness",    f"{_sc_mean('Initial-regime Robustness'):.2%}")
e_col[1].metric("Regime-aware Robustness",      f"{_sc_mean('Regime-aware Robustness'):.2%}")
e_col[2].metric("NPV Municipal Cost (mean)",    f"{_sc_mean('NPV Municipal Cost'):,.0f}")
e_col[3].metric("NPV Flood Damage (mean)",      f"{_sc_mean('NPV Flood Damage'):,.0f}")
e_col[4].metric("Mean ObjectiveStrain",         f"{_sc_mean('Mean ObjectiveStrain'):.3f}")
e_col[5].metric("Option-preserving Early",      f"{_sc_mean('Option-preserving Share Early'):.2%}")

# ObjectiveStrain time series
_has_os = any("ObjectiveStrain" in df.columns and df["ObjectiveStrain"].notna().any() for df in series)
if _has_os:
    st.subheader("F3) ObjectiveStrain time series")
    os_mean_by_yr, os_q10_by_yr, os_q90_by_yr = [], [], []
    for y in years_sorted:
        vals = []
        for df in series:
            if "ObjectiveStrain" not in df.columns:
                continue
            row = df[df["Year"] == y]
            if row.empty:
                continue
            v = pd.to_numeric(row["ObjectiveStrain"], errors="coerce").iloc[0]
            if np.isfinite(v):
                vals.append(float(v))
        os_mean_by_yr.append(float(np.mean(vals)) if vals else np.nan)
        os_q10_by_yr.append(float(np.percentile(vals, 10)) if vals else np.nan)
        os_q90_by_yr.append(float(np.percentile(vals, 90)) if vals else np.nan)

    fig_os = go.Figure()
    fig_os.add_trace(go.Scatter(
        x=years_sorted + years_sorted[::-1],
        y=os_q90_by_yr + os_q10_by_yr[::-1],
        fill="toself", fillcolor="rgba(31,119,180,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="P10–P90",
    ))
    fig_os.add_trace(go.Scatter(
        x=years_sorted, y=os_mean_by_yr, mode="lines",
        name="Mean ObjectiveStrain", line=dict(color="royalblue", width=2),
    ))

    # Draw strain threshold for each regime (if regime shares it)
    all_strains = sorted(set(
        float(rcfg.get("strain_threshold", 0.65))
        for rcfg in res["all_regimes"].values()
    ))
    for _st_val in all_strains:
        fig_os.add_hline(
            y=_st_val, line=dict(color="red", dash="dash"),
            annotation_text=f"strain_threshold={_st_val:.2f}",
        )

    fig_os.update_layout(
        title="ObjectiveStrain over time (mean ± P10–P90)",
        xaxis_title="Year", yaxis_title="ObjectiveStrain (0–1)",
        yaxis=dict(range=[0, 1]),
    )
    st.plotly_chart(fig_os, use_container_width=True, key=f"os_trend_{render_uid}")

# ---- F4) Threshold Satisfaction ----
st.subheader("F4) Threshold Satisfaction over time")

initial_cfg_for_thr = res["all_regimes"].get(res["initial_regime"], res.get("eval_regime_cfg", {}))

if not years_sorted:
    st.info("No yearly results available.")
else:
    active_share: List[float] = []
    initial_share: List[float] = []
    for y in years_sorted:
        active_ok, active_den = 0, 0
        initial_ok, initial_den = 0, 0
        for df in series:
            row_y = df[df["Year"] == y]
            if row_y.empty:
                continue
            row_s = row_y.iloc[0]
            regime_col_y = "ObjectiveRegimeApplied" if "ObjectiveRegimeApplied" in row_y.columns else "ObjectiveRegime"
            active_regime = str(row_s.get(regime_col_y, ""))
            active_cfg = res["all_regimes"].get(active_regime, initial_cfg_for_thr)

            active_den += 1
            active_ok += int(_row_meets_thresholds(row_s, active_cfg.get("thresholds", [])))

            initial_den += 1
            initial_ok += int(_row_meets_thresholds(row_s, initial_cfg_for_thr.get("thresholds", [])))

        active_share.append(float(active_ok / active_den) if active_den > 0 else np.nan)
        initial_share.append(float(initial_ok / initial_den) if initial_den > 0 else np.nan)

    thr_col1, thr_col2 = st.columns(2)

    fig_thr_active = go.Figure()
    fig_thr_active.add_trace(go.Scatter(
        x=years_sorted, y=active_share, mode="lines",
        name="Active regime threshold satisfaction", line=dict(color="seagreen", width=2),
    ))
    fig_thr_active.update_layout(
        title="Active regime threshold satisfaction over time",
        xaxis_title="Year", yaxis_title="Share meeting ObjectiveRegimeApplied thresholds",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
    )
    with thr_col1:
        st.plotly_chart(fig_thr_active, use_container_width=True, key=f"thr_active_{render_uid}")

    fig_thr_initial = go.Figure()
    fig_thr_initial.add_trace(go.Scatter(
        x=years_sorted, y=initial_share, mode="lines",
        name="Initial regime threshold satisfaction", line=dict(color="royalblue", width=2),
    ))
    fig_thr_initial.update_layout(
        title="Initial regime threshold satisfaction over time",
        xaxis_title="Year", yaxis_title=f"Share meeting {res['initial_regime']} thresholds",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
    )
    with thr_col2:
        st.plotly_chart(fig_thr_initial, use_container_width=True, key=f"thr_initial_{render_uid}")

    # Combine all unique thresholds from all regimes for supplementary display.
    _all_thr_rows: List[dict] = []
    _seen_thr: set = set()
    for rname, rcfg in res["all_regimes"].items():
        for t in rcfg.get("thresholds", []):
            key = (str(t.get("metric", "")), t.get("threshold"), t.get("dir"), rname)
            if key not in _seen_thr and t.get("metric"):
                _all_thr_rows.append({**t, "regime": rname})
                _seen_thr.add(key)

    with st.expander("All regime thresholds (supplementary)", expanded=False):
        if not _all_thr_rows:
            st.info("No thresholds available.")
        else:
            fig_thr = go.Figure()
            f_final_rows = []
            for _ti, _t in enumerate(_all_thr_rows):
                metric = str(_t.get("metric", "")).strip()
                thr = float(_t.get("threshold", np.nan))
                direc = str(_t.get("dir", "")).strip().lower()
                rname = str(_t.get("regime", ""))
                if not metric or not np.isfinite(thr) or direc not in {"max", "min"}:
                    continue
                ind_name = f"{metric} ({direc} {thr:g}) [{rname}]"
                clr = base_colorway[_ti % len(base_colorway)]

                y_share = []
                for y in years_sorted:
                    ok, den = 0, 0
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
                        ok += int(v <= thr if direc == "max" else v >= thr)
                    y_share.append(float(ok / den) if den > 0 else np.nan)

                fig_thr.add_trace(go.Scatter(
                    x=years_sorted, y=y_share, mode="lines",
                    name=ind_name, line=dict(color=clr), connectgaps=False,
                ))
                final_share = y_share[-1] if y_share else np.nan
                f_final_rows.append({"Indicator": ind_name, f"Share at {years_sorted[-1]}": final_share})

            fig_thr.update_layout(
                title="Threshold satisfaction share by indicator (all regimes)",
                xaxis_title="Year", yaxis_title="Share meeting threshold",
                yaxis=dict(range=[0, 1], tickformat=".0%"),
            )
            st.plotly_chart(fig_thr, use_container_width=True, key=f"thr_sat_all_{render_uid}")
            st.dataframe(pd.DataFrame(f_final_rows), use_container_width=True, hide_index=True)

# Cost time series
st.subheader("F5) Cost time series (mean across scenarios)")
if years_sorted:
    _psw_res = res.get("policy_switches", [])
    _rsw_res = res.get("regime_switches", [])
    _psc     = float(res.get("policy_switch_cost", 0.0))
    _rsc     = float(res.get("regime_switch_cost", 0.0))

    mc_mean, psw_mean, rsw_mean, tot_mean = [], [], [], []
    for y in years_sorted:
        mc_vals = []
        for df in series:
            row = df[df["Year"] == y]
            if row.empty:
                continue
            v = pd.to_numeric(row.get("Municipal Cost", pd.Series([np.nan])), errors="coerce").iloc[0]
            if np.isfinite(v):
                mc_vals.append(float(v))
        mc_avg = float(np.mean(mc_vals)) if mc_vals else 0.0

        p_cnt = sum(1 for sw in _psw_res for e in sw if int(e[0]) == y)
        r_cnt = sum(1 for sw in _rsw_res for e in sw if int(e[0]) == y)
        p_avg = float(_psc * p_cnt / max(1, len(series)))
        r_avg = float(_rsc * r_cnt / max(1, len(series)))

        mc_mean.append(mc_avg)
        psw_mean.append(p_avg)
        rsw_mean.append(r_avg)
        tot_mean.append(mc_avg + p_avg + r_avg)

    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=mc_mean,  mode="lines", name="Municipal Cost"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=psw_mean, mode="lines", name="Policy Switch Cost"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=rsw_mean, mode="lines", name="Regime Switch Cost"))
    fig_cost.add_trace(go.Scatter(x=years_sorted, y=tot_mean, mode="lines", name="Total", line=dict(width=3)))
    fig_cost.update_layout(title="Mean cost time series", xaxis_title="Year", yaxis_title="Cost")
    st.plotly_chart(fig_cost, use_container_width=True, key=f"cost_ts_{render_uid}")

    f2c1, f2c2, f2c3, f2c4 = st.columns(4)
    f2c1.metric("Municipal Sum",     f"{sum(mc_mean):,.0f}")
    f2c2.metric("Policy Switch Sum", f"{sum(psw_mean):,.0f}")
    f2c3.metric("Regime Switch Sum", f"{sum(rsw_mean):,.0f}")
    f2c4.metric("Total Sum",         f"{sum(tot_mean):,.0f}")

# ---- G) Fixed vs Endogenous Comparison ----
st.divider()
st.header("G) Fixed Objective Regime vs Endogenous Objective Regime Comparison")
st.caption(
    "Runs **Fixed Objective Regime DAPP** (no regime switching) and "
    "**Endogenous Objective Regime DAPP** (ObjectiveStrain-driven switching) "
    "using the **same scenario seeds** from the last main run."
)

enable_cmp = st.checkbox("Enable Fixed vs Endogenous comparison", value=False, key="enable_cmp")

if enable_cmp:
    if "dapp_results" not in st.session_state:
        st.warning("Run DAPP first to generate scenario seeds.")
    else:
        _cseeds = res.get("scenario_seeds", [])
        if not _cseeds:
            st.warning("No scenario seeds found. Run with fixed seed enabled.")
        else:
            st.info(f"Using {len(_cseeds)} scenario seeds from last run.")
            run_cmp = st.button("▶️ Run Comparison", key="run_cmp_btn")

            if run_cmp:
                _cmp_common = dict(
                    years=res["years"],
                    init=DEFAULT_INITIAL,
                    primitives=res["primitives"],
                    params=res["params"],
                    all_regimes=res["all_regimes"],
                    initial_regime_name=res["initial_regime"],
                    k_atp=res["k_consec"],
                    scenario_seeds=_cseeds,
                    cooldown_years=res["cooldown_years"],
                    regime_switch_cost_val=res["regime_switch_cost"],
                    discount_rate_local=res["discount_rate"],
                    decision_mode=res["decision_mode"],
                    lookahead_window_years=res["lookahead_window"],
                    lookahead_weights=res["lookahead_weights"],
                    policy_switch_penalty=res["policy_switch_cost"],
                    strain_window=res["strain_window"],
                    ladder=res["ladder"],
                    lockin_weight=float(res.get("lockin_weight", 0.2)),
                )

                with st.status("Running comparison...", expanded=True) as cmp_st:
                    cmp_st.update(label="Running Fixed Objective Regime DAPP...")
                    _fixed_s, _fixed_psw, _fixed_rsw, _ = run_mc_generalized_with_seeds(
                        objective_regime_mode="Fixed (no regime switching)", **_cmp_common
                    )

                    cmp_st.update(label="Running Endogenous Objective Regime DAPP...")
                    _endo_s, _endo_psw, _endo_rsw, _ = run_mc_generalized_with_seeds(
                        objective_regime_mode="Endogenous (ObjectiveStrain-driven switching)", **_cmp_common
                    )

                    cmp_st.update(label="Computing metrics...")

                    eval_cfg_cmp = res["all_regimes"].get(res["initial_regime"], next(iter(res["all_regimes"].values())))

                    def _make_sc_cmp(ser_l, psw_l, rsw_l):
                        rows = []
                        for i, df in enumerate(ser_l):
                            s = summarize_df(df, eval_cfg_cmp, res["discount_rate"], res["all_regimes"])
                            psw_i = psw_l[i] if i < len(psw_l) else []
                            rsw_i = rsw_l[i] if i < len(rsw_l) else []
                            s["#PolicySwitches"]  = len(psw_i)
                            s["#ObjectiveRegimeSwitches"] = len(rsw_i)
                            s["Cumulative PolicySwitch Cost"] = float(len(psw_i) * res["policy_switch_cost"])
                            s["Cumulative RegimeSwitch Cost"] = float(len(rsw_i) * res["regime_switch_cost"])
                            s["Cumulative Total Cost"] = (
                                s["Cumulative Municipal Cost"]
                                + s["Cumulative PolicySwitch Cost"]
                                + s["Cumulative RegimeSwitch Cost"]
                            )
                            rows.append(s)
                        return pd.DataFrame(rows)

                    _fixed_sc = _make_sc_cmp(_fixed_s, _fixed_psw, _fixed_rsw)
                    _endo_sc  = _make_sc_cmp(_endo_s,  _endo_psw,  _endo_rsw)

                    def _success_rate(ser_l, metric, thr, direc):
                        rates = []
                        for df in ser_l:
                            if metric not in df.columns:
                                continue
                            vals = pd.to_numeric(df[metric], errors="coerce").dropna()
                            if vals.empty:
                                continue
                            rates.append(float((vals <= thr if direc == "max" else vals >= thr).mean()))
                        return float(np.mean(rates)) if rates else np.nan

                    # Threshold-based success rates from initial regime
                    _cmp_thrs = eval_cfg_cmp.get("thresholds", [])
                    success_rows = []
                    for _t in _cmp_thrs:
                        _m   = str(_t.get("metric", ""))
                        _thr = float(_t.get("threshold", np.nan))
                        _dir = str(_t.get("dir", "max"))
                        if not _m or not np.isfinite(_thr):
                            continue
                        success_rows.append({
                            "Metric":           f"{_m} success rate",
                            "Fixed DAPP":       _success_rate(_fixed_s, _m, _thr, _dir),
                            "Endogenous DAPP":  _success_rate(_endo_s,  _m, _thr, _dir),
                        })

                    def _safe_mean(sc, col):
                        return float(sc[col].mean()) if col in sc.columns else np.nan

                    # Near-term policy divergence (first 20 years)
                    _near_yrs = [y for y in res["years"] if y < res["years"][0] + 20]
                    div_vals  = []
                    for i in range(min(len(_fixed_s), len(_endo_s))):
                        n_div, n_tot = 0, 0
                        for yy in _near_yrs:
                            rf = _fixed_s[i][_fixed_s[i]["Year"] == yy]
                            re = _endo_s[i][_endo_s[i]["Year"] == yy]
                            if rf.empty or re.empty:
                                continue
                            n_tot += 1
                            pf_col = "PolicyApplied" if "PolicyApplied" in rf.columns else "Policy"
                            pe_col = "PolicyApplied" if "PolicyApplied" in re.columns else "Policy"
                            if str(rf[pf_col].iloc[0]) != str(re[pe_col].iloc[0]):
                                n_div += 1
                        if n_tot > 0:
                            div_vals.append(n_div / n_tot)
                    near_div = float(np.mean(div_vals)) if div_vals else np.nan

                    _endo_sw_yrs = [int(e[0]) for sw in _endo_rsw for e in sw]
                    _endo_mean_sw = float(np.mean(_endo_sw_yrs)) if _endo_sw_yrs else np.nan

                    scalar_rows = [
                        {"Metric": "Initial-regime Robustness (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Initial-regime Robustness"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Initial-regime Robustness")},
                        {"Metric": "Regime-aware Robustness (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Regime-aware Robustness"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Regime-aware Robustness")},
                        {"Metric": "Cumulative Total Cost (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Cumulative Total Cost"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Cumulative Total Cost")},
                        {"Metric": "NPV Flood Damage (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "NPV Flood Damage"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "NPV Flood Damage")},
                        {"Metric": "Lock-in Years (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Lock-in Years"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Lock-in Years")},
                        {"Metric": "Option-preserving Share Early (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Option-preserving Share Early"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Option-preserving Share Early")},
                        {"Metric": "Mean ObjectiveStrain",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "Mean ObjectiveStrain"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "Mean ObjectiveStrain")},
                        {"Metric": "#ObjectiveRegimeSwitches (mean)",
                         "Fixed DAPP":      _safe_mean(_fixed_sc, "#ObjectiveRegimeSwitches"),
                         "Endogenous DAPP": _safe_mean(_endo_sc, "#ObjectiveRegimeSwitches")},
                        {"Metric": "Mean Regime Switch Year (endogenous only)",
                         "Fixed DAPP":      np.nan,
                         "Endogenous DAPP": _endo_mean_sw},
                        {"Metric": "Near-term policy divergence (first 20 yrs)",
                         "Fixed DAPP":      0.0,
                         "Endogenous DAPP": near_div},
                    ]

                    cmp_df = pd.DataFrame(success_rows + scalar_rows)

                    st.session_state["dapp_comparison"] = {
                        "cmp_df":       cmp_df,
                        "fixed_sc":     _fixed_sc,
                        "endo_sc":      _endo_sc,
                        "fixed_series": _fixed_s,
                        "endo_series":  _endo_s,
                        "near_yrs":     _near_yrs,
                    }
                    cmp_st.update(label="Comparison complete.", state="complete")

    if "dapp_comparison" in st.session_state:
        _c = st.session_state["dapp_comparison"]
        cmp_df = _c["cmp_df"]

        st.subheader("G1) Comparison table")
        st.dataframe(
            cmp_df.style.format({"Fixed DAPP": "{:.4g}", "Endogenous DAPP": "{:.4g}"}),
            use_container_width=True,
        )

        st.subheader("G2) Key metric bar chart")
        _bar_rows = cmp_df[~cmp_df["Fixed DAPP"].isna() | ~cmp_df["Endogenous DAPP"].isna()].copy()
        _bar_rows = _bar_rows[~_bar_rows["Metric"].str.contains("Mean Regime Switch Year")]
        if not _bar_rows.empty:
            fig_gcmp = go.Figure()
            fig_gcmp.add_trace(go.Bar(
                x=_bar_rows["Metric"], y=_bar_rows["Fixed DAPP"],
                name="Fixed DAPP", marker_color="steelblue",
            ))
            fig_gcmp.add_trace(go.Bar(
                x=_bar_rows["Metric"], y=_bar_rows["Endogenous DAPP"],
                name="Endogenous DAPP", marker_color="firebrick",
            ))
            fig_gcmp.update_layout(
                title="Fixed vs Endogenous Objective Regime DAPP",
                barmode="group", xaxis_tickangle=-20, yaxis_title="Value",
            )
            st.plotly_chart(fig_gcmp, use_container_width=True, key=f"gcmp_bar_{render_uid}")

        st.subheader("G3) Near-term policy distribution (first 20 years)")
        _near_yrs_g = _c.get("near_yrs", [])
        _fs = _c.get("fixed_series", [])
        _es = _c.get("endo_series", [])
        if _near_yrs_g and (_fs or _es):
            _g3_pols = sorted({
                p for dflist in [_fs, _es]
                for df in dflist
                for p in _series_text_col(df, "PolicyApplied", "Policy").unique()
            })
            _g3_cols = list(pq.Plotly)

            _pshare = lambda dflist, pnm, yy: sum(
                1 for df in dflist
                if not df[df["Year"] == yy].empty
                and str(df[df["Year"] == yy][
                    "PolicyApplied" if "PolicyApplied" in df.columns else "Policy"
                ].iloc[0]) == pnm
            ) / max(1, len(dflist))

            fig_g3f = go.Figure()
            fig_g3e = go.Figure()
            for _ii, _pn in enumerate(_g3_pols):
                _clr = _g3_cols[_ii % len(_g3_cols)]
                fig_g3f.add_trace(go.Scatter(
                    x=_near_yrs_g,
                    y=[_pshare(_fs, _pn, yy) for yy in _near_yrs_g],
                    mode="lines", stackgroup="one", name=_pn, line=dict(color=_clr),
                ))
                fig_g3e.add_trace(go.Scatter(
                    x=_near_yrs_g,
                    y=[_pshare(_es, _pn, yy) for yy in _near_yrs_g],
                    mode="lines", stackgroup="one", name=_pn, line=dict(color=_clr),
                    showlegend=False,
                ))
            fig_g3f.update_layout(title="Fixed DAPP – policy share (first 20 yrs)", xaxis_title="Year", yaxis_title="Share")
            fig_g3e.update_layout(title="Endogenous DAPP – policy share (first 20 yrs)", xaxis_title="Year", yaxis_title="Share")
            g3c1, g3c2 = st.columns(2)
            with g3c1:
                st.plotly_chart(fig_g3f, use_container_width=True, key=f"g3_fixed_{render_uid}")
            with g3c2:
                st.plotly_chart(fig_g3e, use_container_width=True, key=f"g3_endo_{render_uid}")

        st.download_button(
            "Download comparison CSV",
            cmp_df.to_csv(index=False).encode("utf-8"),
            "dapp_fixed_vs_endogenous_comparison.csv",
            "text/csv",
            key="dl_cmp",
        )

# ========================== Exports ==========================
st.divider()
st.subheader("H) Export")
dl1, dl2, dl3 = st.columns(3)
with dl1:
    st.download_button(
        "Download per-scenario scorecards",
        scorecard.to_csv(index=False).encode("utf-8"),
        "dapp_scorecards.csv", "text/csv", key="dl_sc",
    )
with dl2:
    if not rep_pathways.empty:
        st.download_button(
            "Download representative pathways",
            rep_pathways.to_csv(index=False).encode("utf-8"),
            "dapp_representative_pathways.csv", "text/csv", key="dl_rp",
        )
with dl3:
    # All series as combined CSV
    if series:
        _all_df = pd.concat(
            [df.assign(scenario_id=i) for i, df in enumerate(series)],
            ignore_index=True,
        )
        st.download_button(
            "Download all scenario time series",
            _all_df.to_csv(index=False).encode("utf-8"),
            "dapp_all_scenarios.csv", "text/csv", key="dl_all",
        )
