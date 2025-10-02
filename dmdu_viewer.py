# dmdu_viewer.py (robust Streamlit UI for dmdu_panel.csv)
import os
from typing import List, Dict, Tuple

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="DMDU Panel Explorer", layout="wide")

CORE_METRICS_CANDIDATES = ["Flood Damage", "Ecosystem Level", "Municipal Cost", "Crop Yield"]

# -------------------------
# Loading
# -------------------------
@st.cache_data
def load_panel(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # normalize dtypes
    for k in ["ScenarioID", "RCP", "Sim"]:
        if k in df.columns:
            df[k] = df[k].astype(str)
    # Year to int (robust)
    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").round().astype("Int64")
    # Force metrics numeric
    for m in CORE_METRICS_CANDIDATES:
        if m in df.columns:
            df[m] = pd.to_numeric(df[m], errors="coerce")
    # ScenarioLabel as string if exists
    if "ScenarioLabel" in df.columns:
        df["ScenarioLabel"] = df["ScenarioLabel"].astype(str)
    return df

def find_uncertainty_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c.startswith("unc_")]

def metrics_list(df: pd.DataFrame) -> List[str]:
    return [m for m in CORE_METRICS_CANDIDATES if m in df.columns]

def apply_uncertainty_filters(df: pd.DataFrame, filters: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    if not filters:
        return df
    mask = np.ones(len(df), dtype=bool)
    for col, (lo, hi) in filters.items():
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            mask &= (vals >= lo) & (vals <= hi)
    return df.loc[mask].copy()

def limit_scenarios(df: pd.DataFrame, max_scenarios: int) -> pd.DataFrame:
    if "ScenarioID" not in df.columns:
        return df
    kept = (
        df[["ScenarioID"]].drop_duplicates().sort_values("ScenarioID").head(max_scenarios)["ScenarioID"].tolist()
    )
    return df[df["ScenarioID"].isin(kept)].copy()

def agg_stats(df: pd.DataFrame, group_cols: List[str], metric: str) -> pd.DataFrame:
    """Return group-wise mean/p10/p90 for a single metric, merged into one frame."""
    g = df.groupby(group_cols)[metric]
    a = g.mean().rename(f"{metric}_mean").reset_index()
    p10 = g.quantile(0.10).rename(f"{metric}_p10").reset_index()
    p90 = g.quantile(0.90).rename(f"{metric}_p90").reset_index()
    out = a.merge(p10, on=group_cols).merge(p90, on=group_cols)
    return out

# -------------------------
# Sidebar Controls
# -------------------------
st.sidebar.header("Data Source")
default_path = "output/dmdu_panel.csv"
csv_path = st.sidebar.text_input("Path to dmdu_panel.csv", value=default_path)

try:
    df = load_panel(csv_path)
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

core_metrics = metrics_list(df)
if not core_metrics:
    st.error("No core metrics found (Flood Damage / Ecosystem Level / Municipal Cost / Crop Yield).")
    st.stop()

st.sidebar.header("Filters")

# RCP filter
rcps = sorted(df["RCP"].unique().tolist()) if "RCP" in df.columns else []
sel_rcps = st.sidebar.multiselect("RCP", rcps, default=rcps)

# Scenario limit
max_scenarios = st.sidebar.slider("Max scenarios to display (for plots)", min_value=3, max_value=50, value=12, step=1)

# Year selection for snapshot
min_year = int(df["Year"].dropna().min()) if "Year" in df.columns else 2025
max_year = int(df["Year"].dropna().max()) if "Year" in df.columns else 2100
snap_year = st.sidebar.slider("Snapshot Year", min_value=min_year, max_value=max_year, value=min(max_year, 2100), step=1)

# Uncertainty sliders
unc_cols = find_uncertainty_columns(df)
unc_filters = {}
if unc_cols:
    st.sidebar.subheader("Uncertainty parameter ranges")
    for col in unc_cols:
        cmin = float(np.floor(pd.to_numeric(df[col], errors="coerce").min()*100)/100)
        cmax = float(np.ceil(pd.to_numeric(df[col], errors="coerce").max()*100)/100)
        lo, hi = st.sidebar.slider(col, min_value=cmin, max_value=cmax, value=(cmin, cmax), step=0.01)
        unc_filters[col] = (lo, hi)
else:
    st.sidebar.info("No 'unc_*' columns found.")

# Apply filters
df_filt = df.copy()
if sel_rcps and "RCP" in df.columns:
    df_filt = df_filt[df_filt["RCP"].isin(sel_rcps)]
df_filt = apply_uncertainty_filters(df_filt, unc_filters)

# Informative counters
n_rows = len(df_filt)
n_runs = len(df_filt[["ScenarioID","RCP","Sim"]].drop_duplicates()) if all(c in df_filt.columns for c in ["ScenarioID","RCP","Sim"]) else None
n_scenarios = df_filt[["ScenarioID"]].drop_duplicates().shape[0] if "ScenarioID" in df_filt.columns else None
st.sidebar.markdown(f"**Rows after filter:** {n_rows:,}")
if n_runs is not None:
    st.sidebar.markdown(f"**(Scenario×RCP×Sim) after filter:** {n_runs:,}")
if n_scenarios is not None:
    st.sidebar.markdown(f"**Scenarios after filter:** {n_scenarios:,}")

with st.expander("Preview filtered data (first 10 rows)"):
    st.dataframe(df_filt.head(10), use_container_width=True)

# -------------------------
# Main Layout
# -------------------------
st.title("DMDU Panel Explorer")
st.caption("Explore time series, tradespace snapshots, and filter by uncertainty parameters (unc_*). Scenarios are color-coded.")

tabs = st.tabs(["1) 時系列", "2) スナップショット（トレードスペース）", "3) 不確実性パラメータの幅"])

# -------------------------
# Tab 1: 時系列
# -------------------------
with tabs[0]:
    st.subheader("1) 評価パラメータの時系列グラフ")
    chosen_metrics = st.multiselect("Time-series metrics", core_metrics, default=[m for m in core_metrics[:2]])

    show_band = st.checkbox("Show uncertainty band (p10–p90)", value=True)
    if "ScenarioID" in df_filt.columns and "Year" in df_filt.columns:
        group_cols = [c for c in ["ScenarioID", "ScenarioLabel", "RCP", "Year"] if c in df_filt.columns]
        agg_frames = []
        for metric in chosen_metrics:
            agg_m = agg_stats(df_filt, group_cols, metric)
            agg_frames.append(agg_m)
        if not agg_frames:
            st.info("No metrics selected.")
        else:
            # merge all metrics on group_cols
            agg = agg_frames[0]
            for add in agg_frames[1:]:
                agg = agg.merge(add, on=group_cols, how="outer")
            agg = limit_scenarios(agg, max_scenarios)
            if agg.empty:
                st.info("No data to plot after filtering.")
            else:
                for metric in chosen_metrics:
                    st.markdown(f"**{metric}**")
                    fig = go.Figure()
                    for sid, gsc in agg.groupby("ScenarioID"):
                        name = str(gsc["ScenarioLabel"].iloc[0]) if "ScenarioLabel" in gsc.columns else str(sid)
                        ymean = gsc.get(f"{metric}_mean")
                        if ymean is None or ymean.isna().all():
                            continue
                        fig.add_trace(go.Scatter(
                            x=gsc["Year"], y=ymean,
                            mode="lines",
                            name=name,
                            hovertemplate="Year %{x}<br>Mean %{y:.2f}<extra>"+name+"</extra>"
                        ))
                        if show_band and f"{metric}_p10" in gsc and f"{metric}_p90" in gsc:
                            upper = gsc[f"{metric}_p90"]
                            lower = gsc[f"{metric}_p10"]
                            if not upper.isna().all() and not lower.isna().all():
                                fig.add_trace(go.Scatter(
                                    x=gsc["Year"], y=upper,
                                    mode="lines",
                                    line=dict(width=0),
                                    showlegend=False,
                                    hoverinfo="skip"
                                ))
                                fig.add_trace(go.Scatter(
                                    x=gsc["Year"], y=lower,
                                    mode="lines",
                                    fill="tonexty",
                                    line=dict(width=0),
                                    name=f"{name} p10–p90",
                                    hoverinfo="skip",
                                    showlegend=False
                                ))
                    fig.update_layout(height=450, margin=dict(l=40,r=10,b=10,t=30))
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Required columns missing for time series (ScenarioID, Year).")

# -------------------------
# Tab 2: Snapshot tradespace
# -------------------------
with tabs[1]:
    st.subheader("2) そのとある時間におけるスナップショット（評価指標ごとのトレードスペースとその幅）")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        x_metric = st.selectbox("X-axis metric", core_metrics, index=0)
    with col2:
        y_metric = st.selectbox("Y-axis metric", core_metrics, index=1 if len(core_metrics)>1 else 0)
    with col3:
        agg_fn = st.selectbox("Aggregation across Sim", ["mean (with p10–p90 error bars)", "all points (no agg)"], index=0)

    # Year equality: robust (round+int)
    if "Year" in df_filt.columns:
        df_year = df_filt[df_filt["Year"].astype("Int64") == np.int64(snap_year)].copy()
    else:
        df_year = df_filt.copy()

    if df_year.empty:
        st.info("No data for the selected filters/year.")
    else:
        if agg_fn.startswith("mean"):
            group_cols = [c for c in ["ScenarioID","ScenarioLabel","RCP","Year"] if c in df_year.columns]
            ax = agg_stats(df_year, group_cols, x_metric)
            ay = agg_stats(df_year, group_cols, y_metric)
            agg = ax.merge(ay, on=group_cols, how="inner")
            agg = limit_scenarios(agg, max_scenarios)
            if agg.empty:
                st.info("No scenarios to display after limiting.")
            else:
                fig = px.scatter(
                    agg,
                    x=f"{x_metric}_mean",
                    y=f"{y_metric}_mean",
                    color="ScenarioLabel" if "ScenarioLabel" in agg.columns else "ScenarioID",
                    symbol="RCP" if "RCP" in agg.columns else None,
                    hover_data=group_cols,
                )
                fig.update_traces(
                    error_x=dict(
                        type="data",
                        array=(agg[f"{x_metric}_p90"] - agg[f"{x_metric}_mean"]).to_numpy(),
                        arrayminus=(agg[f"{x_metric}_mean"] - agg[f"{x_metric}_p10"]).to_numpy(),
                        visible=True
                    ),
                    error_y=dict(
                        type="data",
                        array=(agg[f"{y_metric}_p90"] - agg[f"{y_metric}_mean"]).to_numpy(),
                        arrayminus=(agg[f"{y_metric}_mean"] - agg[f"{y_metric}_p10"]).to_numpy(),
                        visible=True
                    ),
                )
                fig.update_layout(height=550, margin=dict(l=40,r=10,b=10,t=30))
                fig.update_xaxes(title=x_metric)
                fig.update_yaxes(title=y_metric)
                st.plotly_chart(fig, use_container_width=True)
        else:
            df_pts = limit_scenarios(df_year, max_scenarios)
            fig = px.scatter(
                df_pts,
                x=x_metric,
                y=y_metric,
                color="ScenarioLabel" if "ScenarioLabel" in df_pts.columns else "ScenarioID",
                symbol="RCP" if "RCP" in df_pts.columns else None,
                opacity=0.6,
                hover_data=[c for c in ["ScenarioID","ScenarioLabel","RCP","Sim"] if c in df_pts.columns],
            )
            fig.update_layout(height=550, margin=dict(l=40,r=10,b=10,t=30))
            st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Tab 3: Uncertainty parameter ranges
# -------------------------
with tabs[2]:
    st.subheader("3) 不確実性パラメータの幅（フィルタで当てはまるケースを絞る）")
    unc_cols = find_uncertainty_columns(df)
    if not unc_cols:
        st.info("No 'unc_*' columns in the dataset.")
    else:
        rng_rows = []
        for col in unc_cols:
            rng_rows.append({
                "parameter": col,
                "min": float(pd.to_numeric(df[col], errors="coerce").min()),
                "max": float(pd.to_numeric(df[col], errors="coerce").max()),
                "selected_min": unc_filters[col][0],
                "selected_max": unc_filters[col][1],
            })
        st.dataframe(pd.DataFrame(rng_rows), use_container_width=True, hide_index=True)

        # histograms
        cols = st.columns(3)
        for i, col in enumerate(unc_cols):
            with cols[i % 3]:
                base = pd.to_numeric(df[col], errors="coerce")
                fig = px.histogram(base.dropna(), x=base.dropna(), nbins=30, opacity=0.6, labels={"x": col})
                # overlay filtered subset
                if not df_filt.empty:
                    sub = pd.to_numeric(df_filt[col], errors="coerce")
                    fig2 = px.histogram(sub.dropna(), x=sub.dropna(), nbins=30, opacity=0.4, labels={"x": col})
                    for tr in fig2.data:
                        tr.name = "filtered"
                        tr.marker = dict(line=dict(width=0.5))
                        fig.add_trace(tr)
                fig.update_layout(height=250, margin=dict(l=10,r=10,t=30,b=10), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

st.caption("Tip: If plots show no traces, check 'Rows after filter' and the preview table, and ensure Year matches integer years (slider).")
