# dapp_guardrails_decision_regimes.py
# Streamlit app: Guardrail-based ATP detection + Decision-Regime-dependent policy ranking.
# Run: streamlit run dapp_guardrails_decision_regimes.py

from __future__ import annotations

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


st.set_page_config(page_title="DAPP Guardrails x Decision Regimes", layout="wide")

if "guardrails_render_uid" not in st.session_state:
    st.session_state["guardrails_render_uid"] = str(uuid.uuid4())
render_uid = st.session_state["guardrails_render_uid"]

st.title("DAPP: Common Guardrails and Decision Regimes")

with st.expander("Overview", expanded=True):
    st.markdown(
        """
This app separates guardrail-based ATP detection from decision-regime-dependent policy selection.
Decision regimes do not change the guardrails or policy candidates; they change how candidate
adaptive actions are ranked after an ATP is reached.

The Monte Carlo percentages shown in representative pathways are occurrence shares of realized
pathways under the same adaptive rule across scenarios, not probabilities of the pathways themselves.
        """
    )


# ========================== Backend imports ==========================
st.sidebar.header("Repository paths")
backend_dir = st.sidebar.text_input("Backend dir", "backend", key="gd_backend_dir")
src_dir = st.sidebar.text_input("Backend src dir", "backend/src", key="gd_src_dir")
sim_dotted = st.sidebar.text_input("Simulation dotted path", "backend.src.simulation", key="gd_sim_dotted")
cfg_dotted = st.sidebar.text_input("Config dotted path", "backend.config", key="gd_cfg_dotted")

for p in [backend_dir, src_dir]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _safe_import(dotted: str):
    try:
        return importlib.import_module(dotted), None
    except Exception as exc:  # pragma: no cover - displayed in Streamlit
        return None, repr(exc)


sim, sim_err = _safe_import(sim_dotted)
cfg, cfg_err = _safe_import(cfg_dotted)

if sim is None:
    st.error(f"Failed to import simulator: {sim_dotted}\n{sim_err}")
    st.stop()
if cfg is None:
    st.error(f"Failed to import config: {cfg_dotted}\n{cfg_err}")
    st.stop()
if not hasattr(sim, "simulate_year"):
    st.error("simulation.py must expose simulate_year(...)")
    st.stop()


# ========================== Defaults ==========================
DEFAULT_PARAMS = dict(cfg.DEFAULT_PARAMS)
rcp_climate_params = dict(cfg.rcp_climate_params)

if "years" in DEFAULT_PARAMS and isinstance(DEFAULT_PARAMS["years"], np.ndarray):
    YEARS_DEFAULT = DEFAULT_PARAMS["years"].astype(int).tolist()
else:
    YEARS_DEFAULT = list(
        range(
            int(DEFAULT_PARAMS.get("start_year", 2026)),
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

DEFAULT_GUARDRAILS = [
    {"metric": "Flood Damage", "threshold": 1_000_000.0, "dir": "max", "weight": 0.35},
    {"metric": "Crop Yield", "threshold": 4_700.0, "dir": "min", "weight": 0.25},
    {"metric": "Ecosystem Level", "threshold": 70.0, "dir": "min", "weight": 0.20},
    {"metric": "Resident Burden", "threshold": 100_000.0, "dir": "max", "weight": 0.20},
]

PRIMITIVE_POLICIES_DEFAULT = {
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

SCORE_METRICS = [
    "guardrail_violation",
    "municipal_cost",
    "future_burden",
    "regret",
]

DEFAULT_DECISION_REGIMES = {
    "Robustness-oriented": {
        "guardrail_violation": 1.0,
        "municipal_cost": 0.0,
        "future_burden": 0.0,
        "regret": 0.0,
    },
    "Cost-efficiency-oriented": {
        "guardrail_violation": 0.5,
        "municipal_cost": 0.5,
        "future_burden": 0.0,
        "regret": 0.0,
    },
    "Future-burden-reduction": {
        "guardrail_violation": 0.5,
        "municipal_cost": 0.0,
        "future_burden": 0.5,
        "regret": 0.0,
    },
    "Balanced-regret-minimization": {
        "guardrail_violation": 0.5,
        "municipal_cost": 0.0,
        "future_burden": 0.0,
        "regret": 0.5,
    },
}

LOCKIN_POLICIES = ["AgriR&D-Boost", "All-Boost"]
IRREVERSIBLE_POLICIES = ["AgriR&D-Boost", "Levee-Boost", "Relocation-Boost", "All-Boost"]
FLEXIBLE_POLICIES = ["NoRegret-Lite", "Nature-Boost"]


# ========================== Sidebar settings ==========================
st.sidebar.header("Simulation settings")


def _parse_years(text: str) -> List[int]:
    text = text.strip()
    if "-" in text:
        a, b = text.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in text.split(",") if x.strip()]


years_str = st.sidebar.text_input(
    "Years (comma or range)", f"{YEARS_DEFAULT[0]}-{YEARS_DEFAULT[-1]}", key="gd_years_str"
)
try:
    YEARS = _parse_years(years_str)
except Exception:
    YEARS = YEARS_DEFAULT
    st.sidebar.warning("Could not parse years; using config defaults.")

rcp_opts = ["(none)"] + [str(k) for k in rcp_climate_params.keys()]
rcp_choice = st.sidebar.selectbox("RCP climate override", rcp_opts, index=0, key="gd_rcp_choice")

params = dict(DEFAULT_PARAMS)
if rcp_choice != "(none)":
    for k, v in rcp_climate_params[float(rcp_choice)].items():
        params[k] = v

n_scenarios = st.sidebar.number_input("Monte Carlo scenarios", 1, 500, 100, 10, key="gd_n_scenarios")
discount_rate = st.sidebar.number_input(
    "Discount rate (NPV)", 0.0, 0.2, 0.03, 0.005, format="%.3f", key="gd_discount_rate"
)
k_consec = st.sidebar.number_input("Performance ATP: consecutive years k", 1, 10, 2, 1, key="gd_k_consec")
policy_switch_cost = st.sidebar.number_input(
    "Policy switch cost", 0.0, 1e12, 100_000.0, 10_000.0, format="%.0f", key="gd_policy_switch_cost"
)
lookahead_window_years = st.sidebar.number_input("Lookahead window (years)", 1, 50, 30, 1, key="gd_lookahead")
early_window_years = st.sidebar.number_input("Early scorecard window (years)", 1, 50, 20, 1, key="gd_early_window")
use_fixed_seed = st.sidebar.checkbox("Use fixed random seed", value=True, key="gd_use_fixed_seed")
base_seed = st.sidebar.number_input("Base seed", 0, 2_147_483_647, 42, 1, key="gd_base_seed")


# ========================== UI inputs ==========================
st.subheader("1) Common Guardrails")
st.caption("Guardrails are shared by every Decision Regime. They define ATP detection only.")

guardrails_df = st.data_editor(
    pd.DataFrame(DEFAULT_GUARDRAILS),
    num_rows="dynamic",
    use_container_width=True,
    key="gd_guardrails_df",
)

GUARDRAILS = guardrails_df.to_dict("records") if not guardrails_df.empty else []

st.subheader("2) Policy Candidates")
st.caption("All Decision Regimes rank the same policy candidates.")

policies_df = pd.DataFrame(PRIMITIVE_POLICIES_DEFAULT).T.reset_index().rename(columns={"index": "policy"})
policies_df = st.data_editor(policies_df, num_rows="dynamic", use_container_width=True, key="gd_policies_df")
if "policy" in policies_df.columns:
    PRIMITIVE_POLICIES = {
        str(row["policy"]): {k: row[k] for k in policies_df.columns if k != "policy"}
        for _, row in policies_df.iterrows()
        if str(row.get("policy", "")).strip()
    }
else:
    PRIMITIVE_POLICIES = dict(PRIMITIVE_POLICIES_DEFAULT)

start_policy = st.selectbox(
    "Initial policy applied in every Decision Regime",
    options=list(PRIMITIVE_POLICIES.keys()),
    index=0,
    key="gd_start_policy",
)

st.subheader("3) Decision Regimes")
st.caption("Decision Regimes differ only in scoring weights used to rank candidate policies after an ATP.")

weights_df = pd.DataFrame.from_dict(DEFAULT_DECISION_REGIMES, orient="index").reset_index()
weights_df = weights_df.rename(columns={"index": "DecisionRegime"})
weights_df = st.data_editor(weights_df, num_rows="dynamic", use_container_width=True, key="gd_decision_weights")

DECISION_REGIMES: Dict[str, Dict[str, float]] = {}
if "DecisionRegime" in weights_df.columns:
    for _, row in weights_df.iterrows():
        name = str(row.get("DecisionRegime", "")).strip()
        if not name:
            continue
        weights: Dict[str, float] = {}
        for m in SCORE_METRICS:
            val = pd.to_numeric(pd.Series([row.get(m, 0.0)]), errors="coerce").iloc[0]
            weights[m] = float(val) if np.isfinite(val) else 0.0
        DECISION_REGIMES[name] = weights


# ========================== Helpers ==========================
def npv(series: List[float], years: List[int], r: float) -> float:
    if not years:
        return 0.0
    y0 = int(years[0])
    return float(sum(float(v) / ((1 + float(r)) ** (int(y) - y0)) for v, y in zip(series, years)))


def _guardrails_clean(guardrails: List[dict]) -> List[dict]:
    rows = []
    for g in guardrails:
        metric = str(g.get("metric", "")).strip()
        if not metric:
            continue
        thr = pd.to_numeric(pd.Series([g.get("threshold")]), errors="coerce").iloc[0]
        if not np.isfinite(thr):
            continue
        direc = str(g.get("dir", "max")).strip().lower()
        if direc not in {"max", "min"}:
            continue
        weight = pd.to_numeric(pd.Series([g.get("weight", 1.0)]), errors="coerce").iloc[0]
        rows.append({"metric": metric, "threshold": float(thr), "dir": direc, "weight": float(weight)})
    return rows


def _violation_severity(value: float, threshold: float, direc: str) -> float:
    if not np.isfinite(value) or not np.isfinite(threshold):
        return 0.0
    if abs(threshold) > 1e-12:
        raw = (value - threshold) / (abs(threshold) + 1e-9) if direc == "max" else (threshold - value) / (abs(threshold) + 1e-9)
    else:
        raw = value - threshold if direc == "max" else threshold - value
    return float(np.clip(raw, 0.0, 1.0))


def row_meets_guardrail(row: pd.Series, guardrail: dict) -> bool:
    metric = str(guardrail.get("metric", "")).strip()
    if not metric or metric not in row.index:
        return True
    value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
    threshold = float(guardrail["threshold"])
    direc = str(guardrail["dir"]).lower()
    if not np.isfinite(value):
        return True
    return bool(value <= threshold if direc == "max" else value >= threshold)


def row_meets_all_guardrails(row: pd.Series, guardrails: List[dict]) -> bool:
    return all(row_meets_guardrail(row, g) for g in guardrails)


def guardrail_pressure_row(row: pd.Series, guardrails: List[dict]) -> float:
    valid = [g for g in guardrails if str(g.get("metric", "")) in row.index]
    if not valid:
        return 0.0
    total_w = sum(max(0.0, float(g.get("weight", 1.0))) for g in valid) or 1.0
    pressure = 0.0
    for g in valid:
        metric = str(g["metric"])
        value = pd.to_numeric(pd.Series([row.get(metric)]), errors="coerce").iloc[0]
        severity = _violation_severity(float(value), float(g["threshold"]), str(g["dir"]))
        pressure += severity * max(0.0, float(g.get("weight", 1.0))) / total_w
    return float(np.clip(pressure, 0.0, 1.0))


def weighted_guardrail_violation(df: pd.DataFrame, guardrails: List[dict]) -> float:
    if df.empty:
        return 0.0
    vals = [guardrail_pressure_row(row, guardrails) for _, row in df.iterrows()]
    return float(np.nanmean(vals)) if vals else 0.0


def future_burden_from_window(df: pd.DataFrame, guardrails: List[dict]) -> float:
    if df.empty:
        return 0.0
    pressures = np.asarray([guardrail_pressure_row(row, guardrails) for _, row in df.iterrows()], dtype=float)
    if len(pressures) == 0:
        return 0.0
    split = max(1, int(np.ceil(len(pressures) / 2)))
    near_pressures = pressures[:split]
    late_pressures = pressures[split:]
    if len(late_pressures) == 0:
        late_pressures = near_pressures
    near_pressure = float(np.nanmean(near_pressures)) if len(near_pressures) else 0.0
    late_pressure = float(np.nanmean(late_pressures)) if len(late_pressures) else near_pressure
    return float(np.clip(0.7 * late_pressure + 0.3 * max(0.0, late_pressure - near_pressure), 0.0, 1.0))


def detect_guardrail_atp(df: pd.DataFrame, guardrails: List[dict], k: int) -> Optional[Tuple[int, str]]:
    if df.empty or "Year" not in df.columns:
        return None
    years = df["Year"].astype(int).tolist()
    best: Optional[Tuple[int, str]] = None
    for g in guardrails:
        metric = str(g.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        run = 0
        for i, (_, row) in enumerate(df.iterrows()):
            fail = not row_meets_guardrail(row, g)
            run = run + 1 if fail else 0
            if run >= int(k):
                start_year = int(years[i - int(k) + 1])
                if best is None or start_year < best[0]:
                    best = (start_year, metric)
                break
    return best


def minmax_norm(values: List[float]) -> List[float]:
    arr = np.asarray(values, dtype=float)
    arr[~np.isfinite(arr)] = np.nan
    if np.all(np.isnan(arr)):
        return [0.0] * len(values)
    lo = float(np.nanmin(arr))
    hi = float(np.nanmax(arr))
    if hi - lo < 1e-12:
        return [0.0] * len(values)
    return [float((v - lo) / (hi - lo)) if np.isfinite(v) else 1.0 for v in arr]


def simulate_candidate_window(
    start_year: int,
    years: List[int],
    prev_values: dict,
    policy: dict,
    params_local: dict,
) -> pd.DataFrame:
    future = [int(y) for y in years if int(y) > int(start_year)]
    rows: List[dict] = []
    state = copy.deepcopy(prev_values)
    for yy in future:
        state, out = sim.simulate_year(int(yy), state, policy, params_local)
        row = out.to_dict() if isinstance(out, pd.Series) else dict(out)
        row["Year"] = int(yy)
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_candidate_policies(
    y: int,
    years: List[int],
    prev_values: dict,
    primitives: Dict[str, dict],
    params_local: dict,
    guardrails: List[dict],
    decision_weights: Dict[str, float],
    lookahead_window: int,
    discount_rate_local: float,
    current_policy_name: str,
    switch_penalty: float,
) -> pd.DataFrame:
    future_years = [int(yy) for yy in years if int(yy) > int(y) and int(yy) <= int(y) + int(lookahead_window)]
    if not future_years:
        return pd.DataFrame([{"policy": current_policy_name, "score": 0.0}])

    rng_state = np.random.get_state()
    rows: List[dict] = []
    try:
        for pname, policy in primitives.items():
            np.random.set_state(rng_state)
            dfw = simulate_candidate_window(int(y), future_years, prev_values, policy, params_local)
            if dfw.empty:
                rows.append({"policy": pname, "score": 0.0})
                continue

            yrs = dfw["Year"].astype(int).tolist()
            municipal = pd.to_numeric(dfw.get("Municipal Cost", pd.Series(np.zeros(len(dfw)))), errors="coerce").fillna(0.0)

            switch_cost = float(switch_penalty) if pname != current_policy_name else 0.0
            rows.append(
                {
                    "policy": pname,
                    "guardrail_violation": weighted_guardrail_violation(dfw, guardrails),
                    "municipal_cost": npv(municipal.tolist(), yrs, discount_rate_local) + switch_cost,
                    "future_burden": future_burden_from_window(dfw, guardrails),
                }
            )
    finally:
        np.random.set_state(rng_state)

    eval_df = pd.DataFrame(rows)
    if eval_df.empty:
        return pd.DataFrame([{"policy": current_policy_name, "score": 0.0}])

    regret_core = ["guardrail_violation", "municipal_cost", "future_burden"]
    regret_norms = {m: minmax_norm(eval_df[m].astype(float).tolist()) for m in regret_core if m in eval_df.columns}
    eval_df["regret"] = [
        float(max((regret_norms[m][i] for m in regret_norms), default=0.0))
        for i in range(len(eval_df))
    ]

    norm_cols = {m: minmax_norm(eval_df[m].astype(float).tolist()) for m in SCORE_METRICS if m in eval_df.columns}
    weights = {m: max(0.0, float(decision_weights.get(m, 0.0))) for m in SCORE_METRICS}
    wsum = sum(weights.values()) or 1.0

    scores = []
    for i in range(len(eval_df)):
        score = 0.0
        for m in SCORE_METRICS:
            score += (weights.get(m, 0.0) / wsum) * float(norm_cols.get(m, [0.0] * len(eval_df))[i])
        scores.append(float(score))
    eval_df["score"] = scores
    return eval_df.sort_values(["score", "policy"], ascending=[True, True]).reset_index(drop=True)


def choose_next_policy(
    y: int,
    years: List[int],
    prev_values: dict,
    current_policy_name: str,
    primitives: Dict[str, dict],
    params_local: dict,
    guardrails: List[dict],
    decision_weights: Dict[str, float],
    lookahead_window: int,
    discount_rate_local: float,
    switch_penalty: float,
) -> Tuple[str, pd.DataFrame]:
    eval_df = evaluate_candidate_policies(
        y=y,
        years=years,
        prev_values=prev_values,
        primitives=primitives,
        params_local=params_local,
        guardrails=guardrails,
        decision_weights=decision_weights,
        lookahead_window=lookahead_window,
        discount_rate_local=discount_rate_local,
        current_policy_name=current_policy_name,
        switch_penalty=switch_penalty,
    )
    if eval_df.empty or "policy" not in eval_df.columns:
        return current_policy_name, eval_df
    return str(eval_df.iloc[0]["policy"]), eval_df


def build_pathway(
    years: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params_local: dict,
    guardrails: List[dict],
    decision_regime_name: str,
    decision_weights: Dict[str, float],
    k_atp: int,
    start_policy_name: str,
    lookahead_window: int,
    discount_rate_local: float,
    switch_penalty: float,
) -> Tuple[pd.DataFrame, List[Tuple[int, str, str]], Dict[str, int]]:
    if not primitives:
        raise ValueError("No policy primitives are defined.")
    if start_policy_name not in primitives:
        start_policy_name = next(iter(primitives))

    current_policy_name = start_policy_name
    current_policy = primitives[current_policy_name]
    prev_values = copy.deepcopy(init)
    out_rows: List[dict] = []
    policy_switches: List[Tuple[int, str, str]] = []
    trigger_counts: Counter[str] = Counter()
    decision_start_year = int(years[0]) if years else 0

    for y in years:
        y = int(y)
        applied_policy_name = current_policy_name
        applied_policy = current_policy

        prev_values, out = sim.simulate_year(y, prev_values, applied_policy, params_local)
        row = out.to_dict() if isinstance(out, pd.Series) else dict(out)
        row["Year"] = y
        row["DecisionRegime"] = decision_regime_name
        row["PolicyApplied"] = applied_policy_name
        row["Policy"] = applied_policy_name
        row["PolicyNext"] = applied_policy_name
        row["ATPTriggered"] = False
        row["GuardrailATPMetric"] = ""
        row["GuardrailPressure"] = guardrail_pressure_row(pd.Series(row), guardrails)
        row["PolicySelectionScore"] = np.nan
        row["Selected_guardrail_violation"] = np.nan
        row["Selected_municipal_cost"] = np.nan
        row["Selected_future_burden"] = np.nan
        row["Selected_regret"] = np.nan

        df_so_far = pd.DataFrame(out_rows + [row])
        df_seg = df_so_far[df_so_far["Year"].astype(int) >= int(decision_start_year)].copy()
        atp = detect_guardrail_atp(df_seg, guardrails, int(k_atp))

        if atp is not None:
            atp_start, atp_metric = atp
            if y == int(atp_start) + int(k_atp) - 1:
                row["ATPTriggered"] = True
                row["GuardrailATPMetric"] = str(atp_metric)
                trigger_counts[str(atp_metric)] += 1
                new_policy, eval_df = choose_next_policy(
                    y=y,
                    years=years,
                    prev_values=prev_values,
                    current_policy_name=applied_policy_name,
                    primitives=primitives,
                    params_local=params_local,
                    guardrails=guardrails,
                    decision_weights=decision_weights,
                    lookahead_window=lookahead_window,
                    discount_rate_local=discount_rate_local,
                    switch_penalty=switch_penalty,
                )
                row["PolicyNext"] = new_policy
                if not eval_df.empty and "policy" in eval_df.columns:
                    best = eval_df[eval_df["policy"].astype(str) == str(new_policy)]
                    if not best.empty and "score" in best.columns:
                        row["PolicySelectionScore"] = float(best.iloc[0]["score"])
                        for metric in SCORE_METRICS:
                            if metric in best.columns:
                                row[f"Selected_{metric}"] = float(best.iloc[0][metric])
                if new_policy != applied_policy_name:
                    policy_switches.append((y, str(atp_metric), str(new_policy)))
                    decision_start_year = y + 1

        out_rows.append(row)

        next_policy_name = str(row["PolicyNext"])
        current_policy_name = next_policy_name if next_policy_name in primitives else applied_policy_name
        current_policy = primitives[current_policy_name]

    return pd.DataFrame(out_rows), policy_switches, dict(trigger_counts)


def run_mc_with_seeds(
    years: List[int],
    scenario_seeds: List[int],
    init: dict,
    primitives: Dict[str, dict],
    params_local: dict,
    guardrails: List[dict],
    decision_regime_name: str,
    decision_weights: Dict[str, float],
    k_atp: int,
    start_policy_name: str,
    lookahead_window: int,
    discount_rate_local: float,
    switch_penalty: float,
) -> Tuple[List[pd.DataFrame], List[List[Tuple[int, str, str]]], List[Dict[str, int]]]:
    series: List[pd.DataFrame] = []
    switches: List[List[Tuple[int, str, str]]] = []
    trigger_counts: List[Dict[str, int]] = []
    for seed in scenario_seeds:
        np.random.seed(int(seed) & 0xFFFFFFFF)
        df_i, sw_i, trig_i = build_pathway(
            years=years,
            init=init,
            primitives=primitives,
            params_local=params_local,
            guardrails=guardrails,
            decision_regime_name=decision_regime_name,
            decision_weights=decision_weights,
            k_atp=k_atp,
            start_policy_name=start_policy_name,
            lookahead_window=lookahead_window,
            discount_rate_local=discount_rate_local,
            switch_penalty=switch_penalty,
        )
        series.append(df_i)
        switches.append(sw_i)
        trigger_counts.append(trig_i)
    return series, switches, trigger_counts


def summarize_df(
    df: pd.DataFrame,
    guardrails: List[dict],
    discount_rate_local: float,
    switches: List[Tuple[int, str, str]],
    trigger_counts: Dict[str, int],
    switch_penalty: float,
    early_window: int,
) -> dict:
    years = df["Year"].astype(int).tolist() if "Year" in df.columns else list(range(len(df)))
    municipal = pd.to_numeric(df.get("Municipal Cost", pd.Series(np.zeros(len(df)))), errors="coerce").fillna(0.0)
    flood = pd.to_numeric(df.get("Flood Damage", pd.Series(np.zeros(len(df)))), errors="coerce").fillna(0.0)
    pressure = pd.to_numeric(df.get("GuardrailPressure", pd.Series(np.zeros(len(df)))), errors="coerce").fillna(0.0)
    policy_col = df.get("PolicyApplied", pd.Series([""] * len(df))).astype(str)

    def _selected_mean(col: str) -> float:
        vals = pd.to_numeric(df.get(col, pd.Series([], dtype=float)), errors="coerce").dropna()
        return float(vals.mean()) if len(vals) else np.nan

    meet_all = [row_meets_all_guardrails(row, guardrails) for _, row in df.iterrows()]
    summary = {
        "Guardrail Robustness": float(np.mean(meet_all)) if meet_all else np.nan,
        "NPV Municipal Cost": npv(municipal.tolist(), years, discount_rate_local),
        "NPV Flood Damage": npv(flood.tolist(), years, discount_rate_local),
        "Cumulative Municipal Cost": float(municipal.sum()),
        "Cumulative PolicySwitch Cost": float(len(switches) * float(switch_penalty)),
        "Cumulative Total Cost": float(municipal.sum() + len(switches) * float(switch_penalty)),
        "Mean GuardrailPressure": float(pressure.mean()) if len(pressure) else np.nan,
        "Max GuardrailPressure": float(pressure.max()) if len(pressure) else np.nan,
        "future_burden": _selected_mean("Selected_future_burden"),
        "regret": _selected_mean("Selected_regret"),
        "Lock-in Years": int(policy_col.isin(LOCKIN_POLICIES).sum()),
        "#PolicySwitches": int(len(switches)),
        "First PolicySwitchYear": int(switches[0][0]) if switches else np.nan,
        "Trigger metrics count": ", ".join(f"{m}:{c}" for m, c in Counter(trigger_counts).most_common()),
    }

    y_start = int(df["Year"].min()) if "Year" in df.columns and not df.empty else 0
    early_mask = df["Year"].astype(int) < y_start + int(early_window) if "Year" in df.columns else pd.Series([True] * len(df))
    early_policies = policy_col[early_mask]
    summary["Option-preserving Share Early"] = float(early_policies.isin(FLEXIBLE_POLICIES).mean()) if len(early_policies) else np.nan

    for g in guardrails:
        metric = str(g.get("metric", "")).strip()
        if not metric or metric not in df.columns:
            continue
        ok = [row_meets_guardrail(row, g) for _, row in df.iterrows()]
        summary[f"Guardrail Robustness [{metric}]"] = float(np.mean(ok)) if ok else np.nan
        summary[f"Trigger count [{metric}]"] = int(trigger_counts.get(metric, 0))

    return summary


def pathway_signature(df: pd.DataFrame, policy_col: str = "PolicyApplied") -> tuple:
    if df.empty:
        return ()
    if policy_col not in df.columns and "Policy" in df.columns:
        policy_col = "Policy"
    years = df["Year"].astype(int).tolist()
    policies = df[policy_col].astype(str).tolist() if policy_col in df.columns else [""] * len(df)
    segments = []
    start = years[0]
    current = policies[0]
    for i in range(1, len(years)):
        if policies[i] != current:
            segments.append((start, years[i - 1], current))
            start, current = years[i], policies[i]
    segments.append((start, years[-1], current))
    return tuple(segments)


def pathway_label(signature: tuple) -> str:
    if not signature:
        return "(empty)"
    return " -> ".join(str(seg[2]) for seg in signature)


def pathway_switch_years(df: pd.DataFrame) -> List[int]:
    return [int(seg[0]) for seg in pathway_signature(df)[1:]]


def summarize_representative_pathways(
    decision_regime_name: str,
    series: List[pd.DataFrame],
    scorecard: pd.DataFrame,
    top_n: int = 8,
) -> pd.DataFrame:
    if not series:
        return pd.DataFrame()
    signatures = [pathway_signature(df) for df in series]
    labels = [pathway_label(sig) for sig in signatures]
    groups: Dict[str, List[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(label, []).append(i)

    rows = []
    total = max(1, len(series))
    for rank, (label, indices) in enumerate(sorted(groups.items(), key=lambda x: -len(x[1]))[:top_n], start=1):
        sc_sub = scorecard.iloc[[i for i in indices if i < len(scorecard)]] if not scorecard.empty else pd.DataFrame()

        def _mean(col: str) -> float:
            return float(sc_sub[col].mean()) if not sc_sub.empty and col in sc_sub.columns else np.nan

        switch_lists = [pathway_switch_years(series[i]) for i in indices if i < len(series)]
        max_len = max((len(v) for v in switch_lists), default=0)
        median_years = []
        for pos in range(max_len):
            vals = [yrs[pos] for yrs in switch_lists if len(yrs) > pos]
            if vals:
                median_years.append(str(int(round(float(np.median(vals))))))

        trigger_metrics = []
        for i in indices:
            if i < len(series) and "GuardrailATPMetric" in series[i].columns:
                trigger_metrics.extend(
                    str(v)
                    for v in series[i]["GuardrailATPMetric"].dropna().astype(str).tolist()
                    if v and str(v).lower() != "nan"
                )
        trig_counts = Counter(trigger_metrics)

        rows.append(
            {
                "DecisionRegime": decision_regime_name,
                "pathway_id": rank,
                "pathway_label": label,
                "representative_scenario_id": int(indices[0]),
                "n_segments": len(signatures[indices[0]]) if indices else 0,
                "median_switch_years": ", ".join(median_years),
                "trigger_metrics": ", ".join(f"{m} ({c})" for m, c in trig_counts.most_common(4)),
                "mean_GuardrailRobustness": _mean("Guardrail Robustness"),
                "mean_NPV_Flood_Damage": _mean("NPV Flood Damage"),
                "mean_NPV_Municipal_Cost": _mean("NPV Municipal Cost"),
                "mean_Cumulative_Total_Cost": _mean("Cumulative Total Cost"),
                "mean_GuardrailPressure": _mean("Mean GuardrailPressure"),
                "mean_future_burden": _mean("future_burden"),
                "mean_regret": _mean("regret"),
                "mean_LockIn_Years": _mean("Lock-in Years"),
                "mean_OptionPreservingShareEarly": _mean("Option-preserving Share Early"),
                "occurrence_count": len(indices),
                "occurrence_share": len(indices) / total,
            }
        )
    return pd.DataFrame(rows)


def generate_scenario_seeds(n: int, fixed: bool, seed: int) -> List[int]:
    rng = np.random.default_rng(int(seed)) if fixed else np.random.default_rng()
    return [int(rng.integers(0, 2**32 - 1)) for _ in range(int(n))]


# ========================== Run ==========================
st.divider()
run_clicked = st.button("Compare all Decision Regimes", key="gd_run_all")

if run_clicked:
    clean_guardrails = _guardrails_clean(GUARDRAILS)
    if not clean_guardrails:
        st.error("At least one valid guardrail is required.")
        st.stop()
    if not DECISION_REGIMES:
        st.error("At least one Decision Regime is required.")
        st.stop()
    if not PRIMITIVE_POLICIES:
        st.error("At least one policy candidate is required.")
        st.stop()

    scenario_seeds = generate_scenario_seeds(int(n_scenarios), bool(use_fixed_seed), int(base_seed))
    all_series: Dict[str, List[pd.DataFrame]] = {}
    all_switches: Dict[str, List[List[Tuple[int, str, str]]]] = {}
    all_trigger_counts: Dict[str, List[Dict[str, int]]] = {}
    scorecards: Dict[str, pd.DataFrame] = {}
    rep_tables: Dict[str, pd.DataFrame] = {}

    with st.status("Running Decision Regime comparison...", expanded=True) as status:
        for dname, weights in DECISION_REGIMES.items():
            status.update(label=f"Running {dname} with shared scenario seeds...")
            series_i, switches_i, triggers_i = run_mc_with_seeds(
                years=YEARS,
                scenario_seeds=scenario_seeds,
                init=DEFAULT_INITIAL,
                primitives=PRIMITIVE_POLICIES,
                params_local=params,
                guardrails=clean_guardrails,
                decision_regime_name=dname,
                decision_weights=weights,
                k_atp=int(k_consec),
                start_policy_name=start_policy,
                lookahead_window=int(lookahead_window_years),
                discount_rate_local=float(discount_rate),
                switch_penalty=float(policy_switch_cost),
            )
            rows = []
            for i, df in enumerate(series_i):
                summary = summarize_df(
                    df=df,
                    guardrails=clean_guardrails,
                    discount_rate_local=float(discount_rate),
                    switches=switches_i[i] if i < len(switches_i) else [],
                    trigger_counts=triggers_i[i] if i < len(triggers_i) else {},
                    switch_penalty=float(policy_switch_cost),
                    early_window=int(early_window_years),
                )
                summary["DecisionRegime"] = dname
                summary["scenario_id"] = i
                summary["scenario_seed"] = scenario_seeds[i] if i < len(scenario_seeds) else np.nan
                rows.append(summary)
            sc_i = pd.DataFrame(rows)
            rep_i = summarize_representative_pathways(dname, series_i, sc_i, top_n=8)
            all_series[dname] = series_i
            all_switches[dname] = switches_i
            all_trigger_counts[dname] = triggers_i
            scorecards[dname] = sc_i
            rep_tables[dname] = rep_i
        status.update(label="Comparison complete.", state="complete")

    st.session_state["gd_results"] = {
        "series": all_series,
        "switches": all_switches,
        "trigger_counts": all_trigger_counts,
        "scorecards": scorecards,
        "rep_tables": rep_tables,
        "guardrails": clean_guardrails,
        "decision_regimes": DECISION_REGIMES,
        "primitives": PRIMITIVE_POLICIES,
        "scenario_seeds": scenario_seeds,
        "years": YEARS,
        "params": params,
        "settings": {
            "n_scenarios": int(n_scenarios),
            "k_consec": int(k_consec),
            "lookahead_window": int(lookahead_window_years),
            "early_window": int(early_window_years),
            "discount_rate": float(discount_rate),
            "policy_switch_cost": float(policy_switch_cost),
            "start_policy": start_policy,
            "seed": int(base_seed) if use_fixed_seed else None,
        },
    }


# ========================== Results ==========================
st.divider()
st.header("Results")

if "gd_results" not in st.session_state:
    st.info("Click Compare all Decision Regimes to run the shared-seed comparison.")
    st.stop()

res = st.session_state["gd_results"]
decision_names = list(res["decision_regimes"].keys())
years_sorted = sorted({int(y) for dflist in res["series"].values() for df in dflist for y in df["Year"].unique()})
policy_names = sorted(
    {
        str(p)
        for dflist in res["series"].values()
        for df in dflist
        for p in df.get("PolicyApplied", pd.Series([], dtype=str)).astype(str).unique()
    }
)
colorway = list(pq.Plotly)
policy_colors = {p: colorway[i % len(colorway)] for i, p in enumerate(policy_names)}
decision_colors = {d: colorway[i % len(colorway)] for i, d in enumerate(decision_names)}


# ---- A) Guardrails and Decision Rule Summary ----
st.subheader("A) Guardrails and Decision Rule Summary")
settings = res["settings"]
summary_cols = st.columns(5)
summary_cols[0].metric("Decision Regimes", len(decision_names))
summary_cols[1].metric("Policy Candidates", len(res["primitives"]))
summary_cols[2].metric("Scenarios", settings["n_scenarios"])
summary_cols[3].metric("ATP k", settings["k_consec"])
summary_cols[4].metric("Lookahead", f"{settings['lookahead_window']} yrs")

with st.expander("Common Guardrails", expanded=True):
    st.dataframe(pd.DataFrame(res["guardrails"]), use_container_width=True, hide_index=True)

with st.expander("Decision Regime scoring weights", expanded=False):
    st.dataframe(pd.DataFrame.from_dict(res["decision_regimes"], orient="index").reset_index().rename(columns={"index": "DecisionRegime"}), use_container_width=True, hide_index=True)

st.caption(
    "All Decision Regimes use the same scenario seeds, guardrails, policy candidates, simulation parameters, and ATP rule. "
    "Only policy-ranking weights differ."
)


# ---- B) Decision Regime Comparison ----
st.subheader("B) Decision Regime Comparison")
all_scorecard = pd.concat(res["scorecards"].values(), ignore_index=True) if res["scorecards"] else pd.DataFrame()

if all_scorecard.empty:
    st.info("No scorecards were produced.")
else:
    compare_metrics = [
        "Guardrail Robustness",
        "NPV Municipal Cost",
        "Mean GuardrailPressure",
        "Max GuardrailPressure",
        "future_burden",
        "regret",
        "Lock-in Years",
        "Option-preserving Share Early",
        "#PolicySwitches",
    ]
    comparison_rows = []
    for dname, sc in res["scorecards"].items():
        row = {"DecisionRegime": dname}
        for metric in compare_metrics:
            row[metric] = float(sc[metric].mean()) if metric in sc.columns else np.nan
        comparison_rows.append(row)
    comparison_df = pd.DataFrame(comparison_rows)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    metric_for_bar = st.selectbox(
        "Comparison metric",
        options=[m for m in compare_metrics if m in comparison_df.columns],
        index=0,
        key="gd_compare_metric",
    )
    fig_cmp = go.Figure()
    fig_cmp.add_trace(
        go.Bar(
            x=comparison_df["DecisionRegime"],
            y=comparison_df[metric_for_bar],
            marker_color=[decision_colors.get(d, "gray") for d in comparison_df["DecisionRegime"]],
            name=metric_for_bar,
        )
    )
    fig_cmp.update_layout(title=f"Decision Regime comparison: {metric_for_bar}", xaxis_title="", yaxis_title=metric_for_bar)
    st.plotly_chart(fig_cmp, use_container_width=True, key=f"gd_cmp_{render_uid}_{metric_for_bar}")


# ---- C) Representative Realized Pathways ----
st.subheader("C) Representative Realized Pathways")
st.caption(
    "Percentages are occurrence shares of realized pathways under the same adaptive rule across Monte Carlo scenarios."
)
rep_all = pd.concat(res["rep_tables"].values(), ignore_index=True) if res["rep_tables"] else pd.DataFrame()
if rep_all.empty:
    st.info("No representative pathways were extracted.")
else:
    d_for_rep = st.selectbox("Decision Regime for pathway table", decision_names, key="gd_rep_decision")
    rep_df = pd.DataFrame(res["rep_tables"].get(d_for_rep, pd.DataFrame())).copy()
    top_n_show = st.slider("Show top N pathways", 1, min(8, len(rep_df)), min(5, len(rep_df)), 1, key="gd_top_paths")
    rep_show = rep_df.head(top_n_show).copy()
    shown_share = float(pd.to_numeric(rep_show.get("occurrence_share", pd.Series([])), errors="coerce").sum())
    if "occurrence_share" in rep_show.columns:
        rep_show["occurrence_share"] = rep_show["occurrence_share"].map("{:.1%}".format)
    st.dataframe(rep_show, use_container_width=True, hide_index=True)
    st.caption(f"Displayed top {top_n_show} pathways account for {shown_share:.1%} of scenarios for {d_for_rep}.")


# ---- D) Policy Composition by Decision Regime ----
st.subheader("D) Policy Composition by Decision Regime")
d_for_policy = st.selectbox("Decision Regime for policy composition", decision_names, key="gd_policy_decision")
series_sel = res["series"].get(d_for_policy, [])

if series_sel and years_sorted:
    data_p = {p: [] for p in policy_names}
    for y in years_sorted:
        total = max(1, len(series_sel))
        counts = Counter()
        for df in series_sel:
            row = df[df["Year"].astype(int) == int(y)]
            if not row.empty:
                counts[str(row["PolicyApplied"].iloc[0])] += 1
        for p in policy_names:
            data_p[p].append(counts[p] / total)

    fig_pol = go.Figure()
    for p in policy_names:
        fig_pol.add_trace(
            go.Scatter(
                x=years_sorted,
                y=data_p[p],
                mode="lines",
                stackgroup="one",
                name=p,
                line=dict(color=policy_colors.get(p)),
            )
        )
    fig_pol.update_layout(title=f"PolicyApplied share: {d_for_policy}", xaxis_title="Year", yaxis_title="Share")
    st.plotly_chart(fig_pol, use_container_width=True, key=f"gd_pol_comp_{render_uid}_{d_for_policy}")


# ---- E) Metro Map ----
st.subheader("E) Metro Map")
d_for_metro = st.selectbox("Decision Regime for metro map", decision_names, key="gd_metro_decision")
bin_size = st.slider("Time bucket (years)", 5, 25, 10, 1, key="gd_metro_bin")
series_m = res["series"].get(d_for_metro, [])

if series_m and years_sorted and policy_names:
    sy, ey = min(years_sorted), max(years_sorted)
    buckets = list(range(sy, ey + 1, int(bin_size)))
    if buckets[-1] != ey:
        buckets.append(ey)
    p_idx = {p: i for i, p in enumerate(policy_names)}
    nodes = {(b, p): 0 for b in buckets for p in policy_names}
    edges: Counter[Tuple[Tuple[int, str], Tuple[int, str]]] = Counter()

    for df in series_m:
        df_l = df[["Year", "PolicyApplied"]].copy()
        df_l["Year"] = df_l["Year"].astype(int)
        bucket_policy: Dict[int, str] = {}
        for i, b0 in enumerate(buckets[:-1]):
            b1 = buckets[i + 1]
            sub = df_l[(df_l["Year"] >= b0) & (df_l["Year"] < b1)]
            if sub.empty:
                continue
            p = str(sub["PolicyApplied"].mode().iloc[0])
            bucket_policy[b0] = p
            nodes[(b0, p)] += 1
        last_b = buckets[-1]
        sub_last = df_l[df_l["Year"] >= last_b]
        if not sub_last.empty:
            p = str(sub_last["PolicyApplied"].mode().iloc[0])
            bucket_policy[last_b] = p
            nodes[(last_b, p)] += 1
        for i in range(len(buckets) - 1):
            b0, b1 = buckets[i], buckets[i + 1]
            if b0 in bucket_policy and b1 in bucket_policy:
                edges[((b0, bucket_policy[b0]), (b1, bucket_policy[b1]))] += 1

    n_sc = max(1, len(series_m))
    fig_m = go.Figure()
    for ((b0, p0), (b1, p1)), count in edges.items():
        sh = count / n_sc
        fig_m.add_trace(
            go.Scatter(
                x=[b0, b1],
                y=[p_idx[p0], p_idx[p1]],
                mode="lines",
                line=dict(width=max(1.0, 18 * sh), color=policy_colors.get(p0, "rgba(80,80,80,0.55)")),
                hovertext=[f"{p0} -> {p1}: {sh:.1%}"] * 2,
                hoverinfo="text",
                showlegend=False,
            )
        )

    nx, ny, ns, nt, nc = [], [], [], [], []
    for (b, p), count in nodes.items():
        if count <= 0:
            continue
        sh = count / n_sc
        nx.append(b)
        ny.append(p_idx[p])
        ns.append(max(8, 40 * sh ** 0.5))
        nt.append(f"{sh:.0%}")
        nc.append(policy_colors.get(p, "gray"))
    fig_m.add_trace(
        go.Scatter(
            x=nx,
            y=ny,
            mode="markers+text",
            marker=dict(size=ns, color=nc, line=dict(color="white", width=0.8)),
            text=nt,
            textposition="top center",
            hoverinfo="text",
            hovertext=[policy_names[int(v)] for v in ny],
            showlegend=False,
        )
    )
    fig_m.update_layout(
        title=f"Metro map: {d_for_metro}",
        xaxis_title="Year",
        yaxis=dict(tickmode="array", tickvals=list(range(len(policy_names))), ticktext=policy_names),
        height=max(420, 55 * len(policy_names)),
    )
    st.plotly_chart(fig_m, use_container_width=True, key=f"gd_metro_{render_uid}_{d_for_metro}_{bin_size}")


# ---- F) Guardrail Satisfaction ----
st.subheader("F) Guardrail Satisfaction")
if years_sorted:
    fig_sat = go.Figure()
    for dname in decision_names:
        series_d = res["series"].get(dname, [])
        y_share = []
        for y in years_sorted:
            ok, den = 0, 0
            for df in series_d:
                row = df[df["Year"].astype(int) == int(y)]
                if row.empty:
                    continue
                den += 1
                ok += int(row_meets_all_guardrails(row.iloc[0], res["guardrails"]))
            y_share.append(ok / den if den else np.nan)
        fig_sat.add_trace(
            go.Scatter(
                x=years_sorted,
                y=y_share,
                mode="lines",
                name=dname,
                line=dict(color=decision_colors.get(dname)),
            )
        )
    fig_sat.update_layout(
        title="Share of scenarios satisfying all common guardrails",
        xaxis_title="Year",
        yaxis_title="Share",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
    )
    st.plotly_chart(fig_sat, use_container_width=True, key=f"gd_sat_all_{render_uid}")

    d_for_guardrail = st.selectbox("Decision Regime for guardrail-by-metric view", decision_names, key="gd_guardrail_metric_decision")
    series_g = res["series"].get(d_for_guardrail, [])
    fig_metric = go.Figure()
    for i, g in enumerate(res["guardrails"]):
        metric = str(g.get("metric", ""))
        if not metric:
            continue
        y_share = []
        for y in years_sorted:
            ok, den = 0, 0
            for df in series_g:
                if metric not in df.columns:
                    continue
                row = df[df["Year"].astype(int) == int(y)]
                if row.empty:
                    continue
                den += 1
                ok += int(row_meets_guardrail(row.iloc[0], g))
            y_share.append(ok / den if den else np.nan)
        fig_metric.add_trace(
            go.Scatter(x=years_sorted, y=y_share, mode="lines", name=metric, line=dict(color=colorway[i % len(colorway)]))
        )
    fig_metric.update_layout(
        title=f"Guardrail satisfaction by metric: {d_for_guardrail}",
        xaxis_title="Year",
        yaxis_title="Share",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
    )
    st.plotly_chart(fig_metric, use_container_width=True, key=f"gd_sat_metric_{render_uid}_{d_for_guardrail}")


# ---- G) Downloads ----
st.subheader("G) Downloads")
dl_cols = st.columns(4)
with dl_cols[0]:
    if not all_scorecard.empty:
        st.download_button(
            "Download scorecards CSV",
            all_scorecard.to_csv(index=False).encode("utf-8"),
            "guardrails_decision_regime_scorecards.csv",
            "text/csv",
            key="gd_dl_scorecards",
        )
with dl_cols[1]:
    if not rep_all.empty:
        st.download_button(
            "Download representative pathways CSV",
            rep_all.to_csv(index=False).encode("utf-8"),
            "guardrails_decision_regime_pathways.csv",
            "text/csv",
            key="gd_dl_pathways",
        )
with dl_cols[2]:
    all_series_rows = []
    for dname, dflist in res["series"].items():
        for i, df in enumerate(dflist):
            all_series_rows.append(df.assign(DecisionRegime=dname, scenario_id=i))
    if all_series_rows:
        all_series_df = pd.concat(all_series_rows, ignore_index=True)
        st.download_button(
            "Download all yearly series CSV",
            all_series_df.to_csv(index=False).encode("utf-8"),
            "guardrails_decision_regime_yearly_series.csv",
            "text/csv",
            key="gd_dl_series",
        )
with dl_cols[3]:
    seeds_df = pd.DataFrame({"scenario_id": list(range(len(res["scenario_seeds"]))), "scenario_seed": res["scenario_seeds"]})
    st.download_button(
        "Download scenario seeds CSV",
        seeds_df.to_csv(index=False).encode("utf-8"),
        "guardrails_decision_regime_scenario_seeds.csv",
        "text/csv",
        key="gd_dl_seeds",
    )
