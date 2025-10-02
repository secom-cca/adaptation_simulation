
# dapp_app.py
# Streamlit UI to build Dynamic Adaptive Policy Pathways (DAPP)
# Repository layout expected:
#   backend/
#     ├─ config.py            (DEFAULT_PARAMS, rcp_climate_params, DATA_DIR paths...)
#     └─ src/
#        ├─ simulation.py     (simulate_year, simulate_simulation)
#        └─ utils.py          (BENCHMARK, aggregate_blocks, calculate_scenario_indicators, ...)
#
# Run:
#   streamlit run dapp_app.py

import json
import os
import sys
import importlib
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="DAPP Pathway Builder", layout="wide")

# Unique render ID to help Streamlit distinguish charts
import uuid
render_uid = st.session_state.setdefault("render_uid", str(uuid.uuid4()))
st.title("Dynamic Adaptive Policy Pathways (DAPP) – Pathway & Scorecard Builder")

with st.expander("ℹ️ Overview"):
    st.markdown("""
This app uses your **backend simulator** to construct **Dynamic Adaptive Policy Pathways (DAPP)**:

- Loads defaults from **backend/config.py** (years, DEFAULT_PARAMS, `rcp_climate_params`, output paths).
- Imports simulator from **backend/src/simulation.py** and helpers from **backend/src/utils.py**.
- Lets you define **ATP thresholds**, **policy primitives**, an escalation **ladder**, and **trigger→action** rules.
- Runs **Monte Carlo**, **detects ATP**, **switches policy**, and outputs **pathways** and a **scorecard**.
""")

# -------------------------- Repo paths & imports --------------------------
st.sidebar.header("Repository paths")
backend_dir = st.sidebar.text_input("Backend dir", "backend")
src_dir = st.sidebar.text_input("Backend src dir", "backend/src")
sim_dotted = st.sidebar.text_input("Simulation dotted path", "backend.src.simulation")
cfg_dotted = st.sidebar.text_input("Config dotted path", "backend.config")
utils_dotted = st.sidebar.text_input("Utils dotted path", "backend.src.utils")

# ensure sys.path
for p in [backend_dir, src_dir]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

# Import modules
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

# sanity checks
for req in ["simulate_year", "simulate_simulation"]:
    if not hasattr(sim, req):
        st.error(f"simulation.py must expose {req}(...)")
        st.stop()

# -------------------------- Load defaults from config --------------------------
DEFAULT_PARAMS = dict(cfg.DEFAULT_PARAMS)
rcp_climate_params = dict(cfg.rcp_climate_params)

# Year range
if "years" in DEFAULT_PARAMS and isinstance(DEFAULT_PARAMS["years"], np.ndarray):
    YEARS_DEFAULT = DEFAULT_PARAMS["years"].astype(int).tolist()
else:
    YEARS_DEFAULT = list(range(int(DEFAULT_PARAMS.get("start_year", 2025)),
                               int(DEFAULT_PARAMS.get("end_year", 2100)) + 1))

# Initial values (sensible defaults leveraging config)
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
    "temp_threshold_crop": DEFAULT_PARAMS.get("temp_threshold_crop_ini", 28.0)
}

# -------------------------- Sidebar: simulation & RCP --------------------------
st.sidebar.header("Simulation settings")

# Years (from config by default)
years_str = st.sidebar.text_input("Years (comma or range)", f"{YEARS_DEFAULT[0]}-{YEARS_DEFAULT[-1]}")
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

# RCP selection
rcp_opts = ["(none)"] + [str(k) for k in rcp_climate_params.keys()]
rcp_choice = st.sidebar.selectbox("RCP climate override", rcp_opts, index=0)
params = dict(DEFAULT_PARAMS)
if rcp_choice != "(none)":
    rcp_key = float(rcp_choice)
    for k, v in rcp_climate_params[rcp_key].items():
        params[k] = v

# Monte Carlo & ATP detection parameters
n_scenarios = st.sidebar.number_input("Monte Carlo scenarios", min_value=1, max_value=300, value=50, step=1)
discount_rate = st.sidebar.number_input("Discount rate (NPV)", min_value=0.0, max_value=0.2, value=0.03, step=0.005, format="%.3f")
k_consec = st.sidebar.number_input("ATP detection: consecutive years (k)", min_value=1, max_value=10, value=2, step=1)

# -------------------------- Thresholds & policies --------------------------
st.subheader("1) ATP thresholds per indicator")
st.caption("dir: 'max' means metric must be ≤ threshold; 'min' means metric must be ≥ threshold.")
DEFAULT_THRESHOLDS = [
    {"metric": "Flood Damage",    "threshold": 5_000_000.0, "dir": "max"},
    {"metric": "available_water", "threshold": 500.0,       "dir": "min"},
    {"metric": "Crop Yield",      "threshold": 2_000.0,     "dir": "min"},
    {"metric": "Ecosystem Level", "threshold": 60.0,        "dir": "min"},
    {"metric": "Resident Burden", "threshold": 100_000.0,   "dir": "max"},
]
thresholds_df = st.data_editor(pd.DataFrame(DEFAULT_THRESHOLDS), num_rows="dynamic")

st.subheader("2) Policy primitives & escalation ladder")
col1, col2 = st.columns([2,1])
with col1:
    PRIMITIVE_POLICIES = {
        "NoRegret-Lite": {
            "planting_trees_amount": 20,  "house_migration_amount": 0,
            "dam_levee_construction_cost": 0, "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 3,  "agricultural_RnD_cost": 1,
            "transportation_invest": 1
        },
        "Nature-Boost": {
            "planting_trees_amount": 150, "house_migration_amount": 20,
            "dam_levee_construction_cost": 0.5, "paddy_dam_construction_cost": 200,
            "capacity_building_cost": 6,  "agricultural_RnD_cost": 1,
            "transportation_invest": 1
        },
        "Levee-Boost": {
            "planting_trees_amount": 50,  "house_migration_amount": 40,
            "dam_levee_construction_cost": 3, "paddy_dam_construction_cost": 0,
            "capacity_building_cost": 6,  "agricultural_RnD_cost": 1,
            "transportation_invest": 1
        },
        "AgriR&D-Boost": {
            "planting_trees_amount": 80,  "house_migration_amount": 10,
            "dam_levee_construction_cost": 0, "paddy_dam_construction_cost": 120,
            "capacity_building_cost": 6,  "agricultural_RnD_cost": 5,
            "transportation_invest": 2
        },
        "Relocation-Boost": {
            "planting_trees_amount": 50,  "house_migration_amount": 150,
            "dam_levee_construction_cost": 1, "paddy_dam_construction_cost": 50,
            "capacity_building_cost": 10, "agricultural_RnD_cost": 1,
            "transportation_invest": 3
        }
    }
    policies_df = pd.DataFrame(PRIMITIVE_POLICIES).T.reset_index().rename(columns={"index": "policy"})
    policies_df = st.data_editor(policies_df, num_rows="dynamic")
    if "policy" in policies_df.columns:
        PRIMITIVE_POLICIES = {
            row["policy"]: {k: row[k] for k in policies_df.columns if k != "policy"}
            for _, row in policies_df.iterrows()
        }
with col2:
    ladder = st.text_area("Escalation ladder (comma-separated)", "NoRegret-Lite,Nature-Boost,Levee-Boost,AgriR&D-Boost,Relocation-Boost")
    ladder = [x.strip() for x in ladder.split(",") if x.strip()]

st.subheader("3) Trigger → policy mapping")
DEFAULT_TRIGGER_MAP = {
    "Flood Damage": "Levee-Boost",
    "available_water": "Nature-Boost",
    "Crop Yield": "AgriR&D-Boost",
    "Ecosystem Level": "Nature-Boost",
    "Resident Burden": "Relocation-Boost"
}
trig_df = st.data_editor(pd.DataFrame([{"metric": k, "next_policy": v} for k, v in DEFAULT_TRIGGER_MAP.items()]), num_rows="dynamic")
trigger_map = {row["metric"]: row["next_policy"] for _, row in trig_df.iterrows() if row.get("metric") and row.get("next_policy")}

# -------------------------- 4) Pathway candidates --------------------------
st.subheader("4) Pathway candidates (multiple plans)")
st.caption("Define multiple candidates. Each has a name, a ladder (list of policy names), and a trigger_map (metric→policy). Policies themselves come from Section 2.")

default_candidates = [
    {
        "name": "Nature-first",
        "ladder": ["NoRegret-Lite","Nature-Boost","AgriR&D-Boost","Levee-Boost","Relocation-Boost"],
        "trigger_map": {
            "Flood Damage": "Levee-Boost",
            "available_water": "Nature-Boost",
            "Crop Yield": "AgriR&D-Boost",
            "Ecosystem Level": "Nature-Boost",
            "Resident Burden": "Relocation-Boost"
        }
    },
    {
        "name": "Defense-first",
        "ladder": ["NoRegret-Lite","Levee-Boost","Relocation-Boost","Nature-Boost","AgriR&D-Boost"],
        "trigger_map": {
            "Flood Damage": "Levee-Boost",
            "available_water": "Nature-Boost",
            "Crop Yield": "AgriR&D-Boost",
            "Ecosystem Level": "Nature-Boost",
            "Resident Burden": "Relocation-Boost"
        }
    }
]

candidates_json = st.text_area("Candidates JSON", json.dumps(default_candidates, indent=2), height=240)
try:
    CANDIDATES = json.loads(candidates_json)
    assert isinstance(CANDIDATES, list) and all("name" in c and "ladder" in c and "trigger_map" in c for c in CANDIDATES)
except Exception as e:
    st.warning(f"Invalid candidates JSON. Using single default from sections above. Error: {e}")
    CANDIDATES = [{"name":"SinglePlan","ladder":ladder,"trigger_map":trigger_map}]

# -------------------------- Core helpers --------------------------
def npv(series: List[float], years: List[int], r: float) -> float:
    if not years:
        return 0.0
    y0 = years[0]
    return float(sum(v / ((1 + r) ** (y - y0)) for v, y in zip(series, years)))

def detect_atp(df: pd.DataFrame, thresholds: pd.DataFrame, k: int) -> Optional[Tuple[int, str]]:
    """Earliest year and metric that fail for k consecutive years."""
    years = df["Year"].tolist()
    for _, row in thresholds.iterrows():
        metric = row["metric"]
        thr = float(row["threshold"])
        direc = row["dir"]
        if metric not in df.columns:
            continue
        vals = df[metric].values
        run = 0
        for i, v in enumerate(vals):
            fail = (v > thr) if direc == "max" else (v < thr)
            run = run + 1 if fail else 0
            if run >= k:
                return years[i - k + 1], metric
    return None

def build_pathway(years: List[int],
                  init: dict,
                  ladder: List[str],
                  primitives: Dict[str, dict],
                  params: dict,
                  thresholds: pd.DataFrame,
                  trig_map: Dict[str, str],
                  k: int,
                  seed: Optional[int] = None) -> Tuple[pd.DataFrame, List[Tuple[int, str, str]]]:
    """Single-scenario pathway with on-the-fly switching using simulate_year."""
    if seed is not None:
        np.random.seed(seed)
    if not hasattr(sim, "simulate_year"):
        raise AttributeError("simulation must expose simulate_year(...)")

    current_policy_name = ladder[0]
    current_policy = primitives[current_policy_name]
    prev_values = dict(init)
    switches = []
    out_rows = []

    for y in years:
        prev_values, outputs = sim.simulate_year(y, prev_values, current_policy, params)
        outputs['Policy'] = current_policy_name
        out_rows.append(outputs)

        # Check ATP using data up to year y
        df = pd.DataFrame(out_rows)
        atp = detect_atp(df, thresholds, k)
        if atp is not None:
            atp_year, atp_metric = atp
            # Switch exactly when the k-th failure year arrives
            if y == atp_year + k - 1:
                # Preferred mapping; else step up ladder
                next_choice = trig_map.get(atp_metric, None)
                if next_choice in primitives:
                    new_policy_name = next_choice
                else:
                    try:
                        idx = ladder.index(current_policy_name)
                        new_policy_name = ladder[min(idx + 1, len(ladder) - 1)]
                    except ValueError:
                        new_policy_name = current_policy_name

                if new_policy_name != current_policy_name:
                    switches.append((int(y), str(atp_metric), str(new_policy_name)))
                    current_policy_name = new_policy_name
                    current_policy = primitives[current_policy_name]

    df_out = pd.DataFrame(out_rows)
    return df_out, switches

def run_mc_pathways(years: List[int],
                    init: dict,
                    ladder: List[str],
                    primitives: Dict[str, dict],
                    params: dict,
                    thresholds: pd.DataFrame,
                    trig_map: Dict[str, str],
                    k: int,
                    n: int) -> Tuple[List[pd.DataFrame], List[List[Tuple[int, str, str]]]]:
    series = []
    switches = []
    for i in range(n):
        # derive a seed per scenario
        seed = int(np.random.SeedSequence().entropy % (2**32 - 1))
        df_i, sw_i = build_pathway(years, init, ladder, primitives, params, thresholds, trig_map, k, seed=seed)
        series.append(df_i)
        switches.append(sw_i)
    return series, switches

# -------------------------- Run button --------------------------

run = st.button("▶️ Run DAPP (Monte Carlo)")

if run:
    with st.status("Running Monte Carlo and constructing pathways for all candidates...", expanded=True) as status:
        all_candidate_series = {}
        all_candidate_switches = {}
        per_scenario_scorecards = []

        for cand in CANDIDATES:
            cname = cand["name"]
            cladder = cand["ladder"]
            ctrig = cand["trigger_map"]
            status.update(label=f"Simulating: {cname}")

            series, switches = run_mc_pathways(YEARS, DEFAULT_INITIAL, cladder, PRIMITIVE_POLICIES, params, thresholds_df, ctrig, k_consec, n_scenarios)
            all_candidate_series[cname] = series
            all_candidate_switches[cname] = switches

            # build scenario-level scorecard for this candidate
            def summarize_df(df: pd.DataFrame) -> dict:
                meet_all = np.ones(len(df), dtype=bool)
                for _, row in thresholds_df.iterrows():
                    m, thr, direc = row["metric"], float(row["threshold"]), row["dir"]
                    if m not in df.columns:
                        continue
                    if direc == "max":
                        meet_all &= (df[m] <= thr)
                    else:
                        meet_all &= (df[m] >= thr)
                robustness_year_share = float(meet_all.sum()) / max(1, len(df))

                npv_cost = npv(df.get("Municipal Cost", pd.Series(np.zeros(len(df)))).tolist(), df["Year"].tolist(), discount_rate)
                npv_damage = npv(df.get("Flood Damage", pd.Series(np.zeros(len(df)))).tolist(), df["Year"].tolist(), discount_rate)

                avg_burden = float(df.get("Resident Burden", pd.Series(np.nan)).mean())
                min_eco = float(df.get("Ecosystem Level", pd.Series(np.nan)).min())
                avg_yield = float(df.get("Crop Yield", pd.Series(np.nan)).mean())
                final_levee = float(df.get("Levee Level", pd.Series(np.nan)).iloc[-1]) if "Levee Level" in df.columns else np.nan

                return {
                    "Candidate": cname,
                    "Robustness": robustness_year_share,
                    "NPV Municipal Cost": npv_cost,
                    "NPV Flood Damage": npv_damage,
                    "Avg Resident Burden": avg_burden,
                    "Min Ecosystem Level": min_eco,
                    "Avg Crop Yield": avg_yield,
                    "Final Levee Level": final_levee,
                    "#Switches": 0  # fill later
                }

            sc_rows = [summarize_df(df) for df in series]
            # fill switches count per scenario
            for i, sc in enumerate(sc_rows):
                sc["#Switches"] = len(switches[i]) if i < len(switches) else 0
            per_scenario_scorecards.extend(sc_rows)

        # Scenario-level table
        scorecard = pd.DataFrame(per_scenario_scorecards)
        st.subheader("A) Per-scenario scorecards (all candidates)")
        st.dataframe(scorecard)

        # Candidate-level aggregate scorecard
        st.subheader("B) Candidate-level aggregate scorecard")
        agg_cols = ["Robustness","NPV Municipal Cost","NPV Flood Damage","Avg Resident Burden","Min Ecosystem Level","Avg Crop Yield","Final Levee Level","#Switches"]
        cand_agg = scorecard.groupby("Candidate")[agg_cols].agg({
            "Robustness":"mean",
            "NPV Municipal Cost":"mean",
            "NPV Flood Damage":"mean",
            "Avg Resident Burden":"mean",
            "Min Ecosystem Level":"mean",
            "Avg Crop Yield":"mean",
            "Final Levee Level":"mean",
            "#Switches":"mean"
        }).reset_index()
        st.dataframe(cand_agg)

        # ---------------- Visual 1: Pathway composition over time ----------------
        # Share of scenarios in each policy per year, for each candidate (stacked area)
        import plotly.graph_objects as go
        st.subheader("C) Pathway composition (stacked share by policy over time)")

        for cname, series in all_candidate_series.items():
            # collect policy per year per scenario
            # Each df has 'Year' and 'Policy' column added earlier
            years_sorted = sorted({int(y) for df in series for y in df["Year"].unique()})
            policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([])).astype(str).unique()})
            # Build matrix: year x policy -> share
            data = {p: [] for p in policy_names}
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
            cum = np.zeros(len(years_sorted))
            for pnm in policy_names:
                fig.add_trace(go.Scatter(
                    x=years_sorted, y=data[pnm],
                    mode="lines", stackgroup="one",
                    name=pnm
                ))
            fig.update_layout(title=f"{cname}: policy share across scenarios", xaxis_title="Year", yaxis_title="Share")
            st.plotly_chart(fig, use_container_width=True, key=f"comp_live_{cname}_{render_uid}")

        # ---------------- Visual 2: Radar chart (normalized) ----------------
        st.subheader("D) Radar chart: candidate comparison (0-100 normalized)")
        # Normalize across candidates; invert where lower is better
        radar_metrics = [
            ("Robustness", False),
            ("NPV Municipal Cost", True),
            ("NPV Flood Damage", True),
            ("Avg Resident Burden", True),
            ("Min Ecosystem Level", False),
            ("Avg Crop Yield", False)
        ]
        # build scales
        scales = {}
        for m, invert in radar_metrics:
            vals = cand_agg[m].values
            vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
            if np.isclose(vmin, vmax):
                vmax = vmin + 1.0
            scales[m] = (vmin, vmax, invert)

        def _norm(m, v):
            vmin, vmax, inv = scales[m]
            score = 100.0 * (v - vmin) / (vmax - vmin)
            if inv:
                score = 100.0 - score
            return float(np.clip(score, 0, 100))

        # make radar
        categories = [m for m, _ in radar_metrics]
        import plotly.graph_objects as go
        fig_radar = go.Figure()
        for _, row in cand_agg.iterrows():
            scores = [_norm(m, row[m]) for m in categories]
            # close the loop
            fig_radar.add_trace(go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]], fill='toself', name=row["Candidate"]))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
        st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_live_{render_uid}")

        # ---------------- Visual 3: Metro map (time × policy) ----------------
        st.subheader("E) Metro map (time × policy pathways)")

        st.caption("Pick a candidate to visualize as a metro-style map. Nodes show the share of scenarios in each policy at time buckets; lines show transition shares between buckets (thicker = more scenarios).")
        cand_names = list(all_candidate_series.keys())
        if cand_names:
            mm_cand = st.selectbox("Candidate for metro map", cand_names, index=0)
            bin_size = st.slider("Time bucket (years)", 5, 25, 10, step=1)

            series = all_candidate_series[mm_cand]
            # Collect all policy names and assign fixed Y lanes
            policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([], dtype=str)).astype(str).unique()})
            y_map = {p: i for i, p in enumerate(policy_names)}
            y_positions = [y_map[p] for p in policy_names]

            # Define buckets
            all_years = sorted({int(y) for df in series for y in df["Year"].unique()})
            if not all_years:
                st.info("No years found for metro map.")
            else:
                start_y, end_y = min(all_years), max(all_years)
                buckets = list(range(start_y, end_y + 1, bin_size))
                if buckets[-1] != end_y:
                    buckets.append(end_y)

                # For each scenario and bucket, decide dominant policy (mode) within that bucket
                import collections
                nodes = {(b, p): 0 for b in buckets for p in policy_names}
                edges = {((buckets[i], a), (buckets[i+1], b)): 0 for i in range(len(buckets)-1) for a in policy_names for b in policy_names}

                for df in series:
                    # Ensure 'Policy' exists
                    if "Policy" not in df.columns:
                        continue
                    # per bucket: mode policy
                    df_local = df[["Year","Policy"]].copy()
                    df_local["Year"] = df_local["Year"].astype(int)
                    scenario_bucket_policy = {}
                    for i, b in enumerate(buckets):
                        if i == len(buckets)-1:
                            mask = (df_local["Year"] >= buckets[i-1]) & (df_local["Year"] <= buckets[i])
                        elif i == 0:
                            mask = (df_local["Year"] >= buckets[i]) & (df_local["Year"] < buckets[i+1])
                        else:
                            mask = (df_local["Year"] >= buckets[i]) & (df_local["Year"] < buckets[i+1])

                        sub = df_local.loc[mask, "Policy"].astype(str)
                        if sub.empty:
                            continue
                        # mode
                        mode_p = sub.mode().iloc[0]
                        scenario_bucket_policy[b] = mode_p
                        nodes[(b, mode_p)] += 1

                    # transitions across consecutive buckets
                    for i in range(len(buckets)-1):
                        b0, b1 = buckets[i], buckets[i+1]
                        if b0 in scenario_bucket_policy and b1 in scenario_bucket_policy:
                            a = scenario_bucket_policy[b0]
                            b = scenario_bucket_policy[b1]
                            edges[((b0, a), (b1, b))] += 1

                # Convert counts to shares
                n_sims = max(1, len(series))
                node_share = {k: v / n_sims for k, v in nodes.items()}
                edge_share = {k: v / n_sims for k, v in edges.items() if v > 0}

                import plotly.graph_objects as go
                figm = go.Figure()

                # Draw edges first (so nodes on top)
                x_map = {b: b for b in buckets}  # x in year units
                for ((b0, a), (b1, b)), sh in edge_share.items():
                    x0, y0 = x_map[b0], y_map[a]
                    x1, y1 = x_map[b1], y_map[b]
                    lw = max(0.5, 12 * sh)  # line width by share
                    figm.add_trace(go.Scatter(
                        x=[x0, x1], y=[y0, y1],
                        mode="lines",
                        line=dict(width=lw),
                        opacity=min(0.9, 0.3 + 0.7*sh),
                        hoverinfo="text",
                        text=[f"{a} → {b}<br>{b0}→{b1}<br>share={sh:.2f}"]*2,
                        showlegend=False
                    ))

                # Draw nodes
                node_x, node_y, node_size, node_text = [], [], [], []
                for (b, p), sh in node_share.items():
                    if sh <= 0:
                        continue
                    node_x.append(x_map[b])
                    node_y.append(y_map[p])
                    node_size.append(max(8, 40 * (sh**0.5)))  # sqrt scaling
                    node_text.append(f"{p}<br>{b}<br>share={sh:.2f}")

                figm.add_trace(go.Scatter(
                    x=node_x, y=node_y, mode="markers+text",
                    marker=dict(size=node_size),
                    text=[p.split('<br>')[0] for p in node_text],
                    textposition="top center",
                    hovertext=node_text, hoverinfo="text",
                    showlegend=False
                ))

                figm.update_layout(
                    title=f"Metro map – {mm_cand}",
                    xaxis_title="Year",
                    yaxis=dict(
                        tickmode="array",
                        tickvals=list(range(len(policy_names))),
                        ticktext=policy_names
                    ),
                    xaxis=dict(range=[start_y - bin_size*0.5, end_y + bin_size*0.5]),
                    height=480
                )
                st.plotly_chart(figm, use_container_width=True, key=f"metro_live_{mm_cand}_{bin_size}_{render_uid}")
        else:
            st.info("No candidates to visualize.")

        # ---------------- Exports ----------------
        st.subheader("E) Export CSVs")
        st.download_button("Download per-scenario scorecards CSV", scorecard.to_csv(index=False).encode("utf-8"), "dapp_scorecards_per_scenario.csv", "text/csv")
        st.download_button("Download candidate aggregate CSV", cand_agg.to_csv(index=False).encode("utf-8"), "dapp_scorecards_candidate.csv", "text/csv")

        st.success("All candidates processed.")

        # ---- Persist results in session_state so UI changes won't reset them ----
        st.session_state["dapp_results"] = {
            "all_candidate_series": all_candidate_series,
            "all_candidate_switches": all_candidate_switches,
            "scorecard_per_scenario": scorecard,
            "candidate_aggregate": cand_agg,
            "thresholds_df": thresholds_df.copy(),
            "candidates": CANDIDATES,
            "policies": PRIMITIVE_POLICIES,
            "years": YEARS,
            "k_consec": k_consec,
            "discount_rate": discount_rate,
            "n_scenarios": n_scenarios,
            "params": params
        }

else:
    st.info("Configure thresholds/policies, candidates and choose RCP (optional), then click **Run DAPP (Monte Carlo)**.")
    st.success("Modules imported successfully.")

# -------------------- Reuse results across reruns --------------------
st.divider()
st.subheader("Results (persisted)")
if (not run) and ("dapp_results" in st.session_state):
    res = st.session_state["dapp_results"]

    # Optional: clear results
    colc1, colc2 = st.columns([1,3])
    with colc1:
        if st.button("🧹 Clear results"):
            del st.session_state["dapp_results"]
            st.experimental_rerun()
    with colc2:
        st.caption("Showing last computed results. Changing candidates/policies won't recompute until you click **Run DAPP** again.")

    # Pull variables
    all_candidate_series = res["all_candidate_series"]
    all_candidate_switches = res["all_candidate_switches"]
    scorecard = pd.DataFrame(res["scorecard_per_scenario"])
    cand_agg = pd.DataFrame(res["candidate_aggregate"])

    # -- Re-render key tables --
    st.markdown("**Per-scenario scorecards (last run)**")
    st.dataframe(scorecard)

    st.markdown("**Candidate-level aggregate scorecard (last run)**")
    st.dataframe(cand_agg)

    # ---------------- Visual 1: Pathway composition ----------------
    import plotly.graph_objects as go
    st.subheader("Pathway composition (share by policy over time) — last run")
    for cname, series in all_candidate_series.items():
        years_sorted = sorted({int(y) for df in series for y in df["Year"].unique()})
        policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([], dtype=str)).astype(str).unique()})
        data = {p: [] for p in policy_names}
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
            fig.add_trace(go.Scatter(x=years_sorted, y=data[pnm], mode="lines", stackgroup="one", name=pnm))
        fig.update_layout(title=f"{cname}: policy share across scenarios (last run)", xaxis_title="Year", yaxis_title="Share")
        st.plotly_chart(fig, use_container_width=True, key=f"comp_live_{cname}_{render_uid}")

    # ---------------- Visual 2: Radar chart ----------------
    st.subheader("Radar chart: candidate comparison (last run)")
    radar_metrics = [
        ("Robustness", False),
        ("NPV Municipal Cost", True),
        ("NPV Flood Damage", True),
        ("Avg Resident Burden", True),
        ("Min Ecosystem Level", False),
        ("Avg Crop Yield", False)
    ]
    scales = {}
    for m, invert in radar_metrics:
        vals = cand_agg[m].values
        vmin, vmax = float(np.nanmin(vals)), float(np.nanmax(vals))
        if np.isclose(vmin, vmax):
            vmax = vmin + 1.0
        scales[m] = (vmin, vmax, invert)
    def _norm(m, v):
        vmin, vmax, inv = scales[m]
        score = 100.0 * (v - vmin) / (vmax - vmin)
        if inv:
            score = 100.0 - score
        return float(np.clip(score, 0, 100))
    categories = [m for m, _ in radar_metrics]
    fig_radar = go.Figure()
    for _, row in cand_agg.iterrows():
        scores = [_norm(m, row[m]) for m in categories]
        fig_radar.add_trace(go.Scatterpolar(r=scores + [scores[0]], theta=categories + [categories[0]], fill='toself', name=row["Candidate"]))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
    st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_live_{render_uid}")

    # ---------------- Visual 3: Metro map ----------------
    st.subheader("Metro map (last run)")
    cand_names = list(all_candidate_series.keys())
    if cand_names:
        mm_cand = st.selectbox("Candidate for metro map (last run)", cand_names, index=0, key="mm_last_run_cand")
        bin_size = st.slider("Time bucket (years)", 5, 25, 10, step=1, key="mm_last_run_bins")
        series = all_candidate_series[mm_cand]
        policy_names = sorted({p for df in series for p in df.get("Policy", pd.Series([], dtype=str)).astype(str).unique()})
        y_map = {p: i for i, p in enumerate(policy_names)}
        all_years = sorted({int(y) for df in series for y in df["Year"].unique()})
        if all_years:
            start_y, end_y = min(all_years), max(all_years)
            buckets = list(range(start_y, end_y + 1, bin_size))
            if buckets[-1] != end_y:
                buckets.append(end_y)
            nodes = {(b, p): 0 for b in buckets for p in policy_names}
            edges = {((buckets[i], a), (buckets[i+1], b)): 0 for i in range(len(buckets)-1) for a in policy_names for b in policy_names}
            for df in series:
                if "Policy" not in df.columns:
                    continue
                df_local = df[["Year","Policy"]].copy()
                df_local["Year"] = df_local["Year"].astype(int)
                scenario_bucket_policy = {}
                for i, b in enumerate(buckets):
                    if i == len(buckets)-1:
                        mask = (df_local["Year"] >= buckets[i-1]) & (df_local["Year"] <= buckets[i])
                    elif i == 0:
                        mask = (df_local["Year"] >= buckets[i]) & (df_local["Year"] < buckets[i+1])
                    else:
                        mask = (df_local["Year"] >= buckets[i]) & (df_local["Year"] < buckets[i+1])
                    sub = df_local.loc[mask, "Policy"].astype(str)
                    if sub.empty:
                        continue
                    mode_p = sub.mode().iloc[0]
                    scenario_bucket_policy[b] = mode_p
                    nodes[(b, mode_p)] += 1
                for i in range(len(buckets)-1):
                    b0, b1 = buckets[i], buckets[i+1]
                    if b0 in scenario_bucket_policy and b1 in scenario_bucket_policy:
                        a = scenario_bucket_policy[b0]
                        b = scenario_bucket_policy[b1]
                        edges[((b0, a), (b1, b))] += 1
            n_sims = max(1, len(series))
            node_share = {k: v / n_sims for k, v in nodes.items()}
            edge_share = {k: v / n_sims for k, v in edges.items() if v > 0}
            import plotly.graph_objects as go
            figm = go.Figure()
            x_map = {b: b for b in buckets}
            for ((b0, a), (b1, b)), sh in edge_share.items():
                x0, y0 = x_map[b0], y_map[a]
                x1, y1 = x_map[b1], y_map[b]
                lw = max(0.5, 12 * sh)
                figm.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(width=lw), opacity=min(0.9, 0.3 + 0.7*sh), hoverinfo="text", text=[f"{a} → {b}<br>{b0}→{b1}<br>share={sh:.2f}"]*2, showlegend=False))
            node_x, node_y, node_size, node_text = [], [], [], []
            for (b, pnm), sh in node_share.items():
                if sh <= 0:
                    continue
                node_x.append(x_map[b])
                node_y.append(y_map[pnm])
                node_size.append(max(8, 40 * (sh**0.5)))
                node_text.append(f"{pnm}<br>{b}<br>share={sh:.2f}")
            figm.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text", marker=dict(size=node_size), text=[t.split('<br>')[0] for t in node_text], textposition="top center", hovertext=node_text, hoverinfo="text", showlegend=False))
            figm.update_layout(title=f"Metro map – {mm_cand} (last run)", xaxis_title="Year", yaxis=dict(tickmode="array", tickvals=list(range(len(policy_names))), ticktext=policy_names), height=480)
            st.plotly_chart(figm, use_container_width=True, key=f"metro_live_{mm_cand}_{bin_size}_{render_uid}")
    else:
        st.info("No persisted results yet. Click **Run DAPP** above.")


if run:
    with st.status("Running Monte Carlo and constructing pathways...", expanded=True) as status:
        status.update(label="Simulating scenarios...")
        series, switches = run_mc_pathways(YEARS, DEFAULT_INITIAL, ladder, PRIMITIVE_POLICIES, params, thresholds_df, trigger_map, k_consec, n_scenarios)

        # ---- Scorecard aggregation ----
        status.update(label="Aggregating results for scorecard...")

        def summarize_df(df: pd.DataFrame) -> dict:
            # robustness: share of years meeting all thresholds
            meet_all = np.ones(len(df), dtype=bool)
            for _, row in thresholds_df.iterrows():
                m, thr, direc = row["metric"], float(row["threshold"]), row["dir"]
                if m not in df.columns:
                    continue
                if direc == "max":
                    meet_all &= (df[m] <= thr)
                else:
                    meet_all &= (df[m] >= thr)
            robustness_year_share = float(meet_all.sum()) / max(1, len(df))

            # costs/damages NPVs
            npv_cost = npv(df.get("Municipal Cost", pd.Series(np.zeros(len(df)))).tolist(), df["Year"].tolist(), discount_rate)
            npv_damage = npv(df.get("Flood Damage", pd.Series(np.zeros(len(df)))).tolist(), df["Year"].tolist(), discount_rate)

            # other aggregates
            avg_burden = float(df.get("Resident Burden", pd.Series(np.nan)).mean())
            min_eco = float(df.get("Ecosystem Level", pd.Series(np.nan)).min())
            avg_yield = float(df.get("Crop Yield", pd.Series(np.nan)).mean())
            final_levee = float(df.get("Levee Level", pd.Series(np.nan)).iloc[-1]) if "Levee Level" in df.columns else np.nan

            return {
                "Robustness (year-share meeting all thresholds)": robustness_year_share,
                "NPV Municipal Cost": npv_cost,
                "NPV Flood Damage": npv_damage,
                "Avg Resident Burden": avg_burden,
                "Min Ecosystem Level": min_eco,
                "Avg Crop Yield": avg_yield,
                "Final Levee Level": final_levee
            }

        summaries = [summarize_df(df) for df in series]
        scorecard = pd.DataFrame(summaries)
        scorecard["#Switches"] = [len(sw) for sw in switches]
        scorecard["Pathway (switches)"] = [", ".join([f"{y}:{m}->{p}" for (y,m,p) in sw]) if sw else "(no switch)" for sw in switches]

        # Optional: block aggregation & indicators using utils
        try:
            blocks_all = []
            for i, df in enumerate(series):
                agg_blocks = utl.aggregate_blocks(df)
                blocks_all.append({"scenario": i, "blocks": agg_blocks, "indic": utl.calculate_scenario_indicators(df)})
            status.update(label="Computed block aggregates via utils.py")
        except Exception as e:
            blocks_all = []
            st.info(f"aggregate_blocks failed (optional): {e}")

        # Write decision log if config path exists
        try:
            action_log = getattr(cfg, "ACTION_LOG_FILE", None)
            if action_log is not None:
                rows = []
                for i, sw in enumerate(switches):
                    for (y, m, p) in sw:
                        rows.append({"Scenario": i, "Year": y, "Metric": m, "NewPolicy": p})
                if rows:
                    os.makedirs(os.path.dirname(action_log), exist_ok=True)
                    pd.DataFrame(rows).to_csv(action_log, index=False)
                    st.success(f"Decision log written: {action_log}")
        except Exception as e:
            st.info(f"Could not write decision log: {e}")

        st.success("Done. See results below.")

    # -------------------------- Results --------------------------
    st.subheader("A) Pathway logs (per scenario)")
    st.caption("Each row shows the sequence of switches taken in that Monte Carlo scenario.")
    st.dataframe(scorecard[["#Switches", "Pathway (switches)"]])

    st.subheader("B) Scorecard")
    st.dataframe(scorecard)


    st.subheader("C) Average trajectory (across scenarios)")
    # ---- Robust averaging over scenarios ----
    # 1) Keep only numeric columns (drop dict/list/object like 'planting_history')
    numeric_aligned = []
    for df in series:
        df_num = df.select_dtypes(include=[np.number]).copy()
        # ensure Year present and is int
        if "Year" in df_num.columns:
            df_num["Year"] = df_num["Year"].astype(int)
            df_num = df_num.set_index("Year")
        else:
            # if Year got dropped for some reason, recover from original df
            df_num = df.assign(Year=df["Year"]).select_dtypes(include=[np.number]).set_index("Year")
        numeric_aligned.append(df_num)

    # 2) Outer-join on Year to accommodate misaligned horizons; then average numeric-only
    merged = pd.concat(numeric_aligned, axis=1, keys=range(len(numeric_aligned)))
    # Group by the row index (Year) and mean across scenario columns only
    avg_df = merged.groupby(level=0).mean(numeric_only=True)
    avg_df = avg_df.reset_index().rename(columns={"index": "Year"})

    st.dataframe(avg_df)

    st.subheader("D) Export CSVs")
    st.download_button("Download Scorecard CSV", scorecard.to_csv(index=False).encode("utf-8"), "dapp_scorecard.csv", "text/csv")
    st.download_button("Download Average Trajectory CSV", avg_df.to_csv(index=False).encode("utf-8"), "dapp_average_trajectory.csv", "text/csv")


    # Optional plots using utils helpers (if desired by user, they can add)
    st.subheader("E) Optional: Block aggregates (from utils)")
    if blocks_all:
        # Show a compact JSON-like view
        st.json(blocks_all)

else:
    st.info("Configure thresholds/policies, choose RCP (optional), then click **Run DAPP (Monte Carlo)**.")
    st.success("Modules imported successfully.")
