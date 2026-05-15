import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException, WebSocket, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from typing import Dict, Any, List

from config import (
    DEFAULT_PARAMS, rcp_climate_params, RANK_FILE, ACTION_LOG_FILE, YOUR_NAME_FILE,
    MANA_JPY_PER_YEAR, BASE_POLICY_BUDGET_MANA, BASE_POLICY_BUDGET_JPY_PER_YEAR,
    TURN_YEARS, POLICY_MANA_RULES, POLICY_EFFECT_METADATA, EVENT_THRESHOLDS,
)
from models import (
    SimulationRequest, SimulationResponse, CompareRequest, CompareResponse,
    DecisionVar, CurrentValues, BlockRaw,
    IntermediateEvaluationRequest, IntermediateEvaluationResponse,
    ResidentCouncilResponse, ResidentInterviewRequest, ResidentInterviewResponse,
)
from intermediate_evaluation import generate_intermediate_evaluation
from resident_council import generate_resident_council, generate_resident_interview
from simulation import generate_ai_commentary, simulate_simulation, simulate_year
from utils import calculate_scenario_indicators, aggregate_blocks

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scenarios_data: Dict[str, pd.DataFrame] = {}

def _data_file(path: Path) -> Path:
    if path.exists():
        return path
    backend_data_path = Path(__file__).parent / "data" / path.name
    return backend_data_path

def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        if not np.isfinite(numeric):
            return None
        return numeric
    return value

COMPARISON_RESULTS_FILE = Path(__file__).parent / "data" / "comparison_results.tsv"

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/policy-config")
def get_policy_config():
    return _json_safe({
        "MANA_JPY_PER_YEAR": MANA_JPY_PER_YEAR,
        "BASE_POLICY_BUDGET_MANA": BASE_POLICY_BUDGET_MANA,
        "BASE_POLICY_BUDGET_JPY_PER_YEAR": BASE_POLICY_BUDGET_JPY_PER_YEAR,
        "TURN_YEARS": TURN_YEARS,
        "POLICY_MANA_RULES": POLICY_MANA_RULES,
        "POLICY_EFFECT_METADATA": POLICY_EFFECT_METADATA,
        "EVENT_THRESHOLDS": EVENT_THRESHOLDS,
    })

@app.post("/simulate", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    scenario_name = req.scenario_name
    mode = req.mode
    decision_df = pd.DataFrame([dv.model_dump() for dv in req.decision_vars]) if req.decision_vars else pd.DataFrame()

    # Update params based on RCP scenario and current values
    params = DEFAULT_PARAMS.copy()
    
    # RCPパラメータの取得を修正
    rcp_value = req.decision_vars[0].cp_climate_params
    
    # 浮動小数点数の比較問題を回避するため、最も近い値を見つける
    available_rcp_values = list(rcp_climate_params.keys())
    closest_rcp = min(available_rcp_values, key=lambda x: abs(x - rcp_value))
    
    rcp_param = rcp_climate_params[closest_rcp]
    params.update(rcp_param)
    

    all_df = pd.DataFrame()
    block_scores = []

    if mode == "Monte Carlo Simulation Mode":
        results = []
        for sim in range(req.num_simulations):
            # Use a per-sim seed so each sim differs, but pair scenario and baseline with same seed
            params_sim = params.copy()
            base_seed = params.get("SIMULATION_RANDOM_SEED", None)
            if base_seed is not None:
                params_sim["SIMULATION_RANDOM_SEED"] = int(base_seed) + int(sim)

            # run scenario simulation
            sim_result = simulate_simulation(
                years=params_sim['years'],
                initial_values=req.current_year_index_seq.model_dump(),
                decision_vars_list=decision_df,
                params=params_sim,
                fixed_seed=True
            )

            # prepare a zero/no-policy decision set for baseline (same structure)
            zero_decisions = None
            if isinstance(decision_df, pd.DataFrame) and not decision_df.empty:
                zero_df = decision_df.copy()
                for c in zero_df.columns:
                    zero_df[c] = 0
                zero_decisions = zero_df
            elif isinstance(decision_df, list) and decision_df:
                zero_list = []
                for _ in decision_df:
                    zero_list.append({k: 0 for k in decision_df[0].keys()})
                zero_decisions = zero_list
            else:
                zero_decisions = decision_df

            # run explicit baseline simulation using same params_sim (seed)
            baseline_result = simulate_simulation(
                years=params_sim['years'],
                initial_values=req.current_year_index_seq.model_dump(),
                decision_vars_list=zero_decisions,
                params=params_sim,
                fixed_seed=True
            )

            df_sim = pd.DataFrame(sim_result)
            df_base = pd.DataFrame(baseline_result)

            # attach explicit baseline flood and difference per year (align by Year)
            if not df_base.empty and not df_sim.empty:
                df_merged = df_sim.merge(df_base[['Year', 'Flood Damage JPY']], on='Year', how='left', suffixes=('', '_baseline_explicit'))
                df_merged['Baseline Flood Damage JPY (explicit)'] = df_merged['Flood Damage JPY_baseline_explicit']
                df_merged['Damage Difference JPY (baseline - scenario)'] = df_merged['Baseline Flood Damage JPY (explicit)'] - df_merged['Flood Damage JPY']
            else:
                df_merged = df_sim

            df_merged["Simulation"] = sim
            results.append(df_merged)
        all_df = pd.concat(results, ignore_index=True)
        block_scores = []

    elif mode == "Sequential Decision-Making Mode":
        year = req.decision_vars[0].year
        current_values_input = req.current_year_index_seq.model_dump()
        decision_vars = decision_df.iloc[0].to_dict()
        
        # simulate_yearを1年分だけ回す
        current_values_output, outputs = simulate_year(
            year=year,
            prev_values=current_values_input,
            decision_vars=decision_vars,
            params=params,
            fixed_seed=True
        )
        result = [outputs]  # simulate_simulation と同じ形式で返すためリストに

        all_df = pd.DataFrame(result)
        block_scores = aggregate_blocks(all_df)

        # ログ保存
        df_log = pd.DataFrame([dv.model_dump() for dv in req.decision_vars])
        df_log['user_name'] = req.user_name
        df_log['scenario_name'] = scenario_name
        df_log['timestamp'] = pd.Timestamp.utcnow()
        if ACTION_LOG_FILE.exists():
            df_old = pd.read_csv(ACTION_LOG_FILE)
            df_combined = pd.concat([df_old, df_log], ignore_index=True)
        else:
            df_combined = df_log
        df_combined.to_csv(ACTION_LOG_FILE, index=False)

        df_csv = pd.DataFrame(block_scores)
        df_csv['user_name'] = req.user_name
        df_csv['scenario_name'] = scenario_name
        df_csv['timestamp'] = pd.Timestamp.utcnow()
        df_csv['user_name'].to_csv(YOUR_NAME_FILE, index=False)
        if RANK_FILE.exists():
            old = pd.read_csv(RANK_FILE, sep='\t')
            merged = (
                old.set_index(['user_name', 'scenario_name', 'period'])
                .combine_first(df_csv.set_index(['user_name', 'scenario_name', 'period']))
                .reset_index()
            )
            merged.to_csv(RANK_FILE, sep='\t', index=False)
        else:
            df_csv.to_csv(RANK_FILE, sep='\t', index=False)

    
    elif mode == "Predict Simulation Mode":
        # 全期間の予測値を計算する
        # paramsは既にRCPパラメータで更新済みなので、再度コピーしない
        sim_years = np.arange(req.decision_vars[0].year, params['end_year'] + 1)
        seq_result = simulate_simulation(
            years=sim_years,
            initial_values=req.current_year_index_seq.model_dump(),
            decision_vars_list=decision_df,
            params=params,
            fixed_seed=True
        )

        all_df = pd.DataFrame(seq_result)
        block_scores = []

    elif mode == "Record Results Mode":
        import shutil
        import glob
        from pathlib import Path

        src_dir = Path(__file__).parent / "data"
        dst_dir = Path(__file__).parent.parent / "frontend" / "public" / "results" / "data"
        dst_dir.mkdir(parents=True, exist_ok=True)

        for filepath in glob.glob(str(src_dir / "*.csv")) + glob.glob(str(src_dir / "*.tsv")):
            shutil.copy(filepath, dst_dir)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    if mode != "Predict Simulation Mode":
        scenarios_data[scenario_name] = all_df.copy()

    if mode == "Sequential Decision-Making Mode":
        return {
            "scenario_name": scenario_name,
            "data": result,
            "current_values": current_values_output,
            "block_scores": block_scores
        }
    else:
        return SimulationResponse(
            scenario_name=scenario_name,
            data=all_df.to_dict(orient="records"),
            block_scores=block_scores
        )

@app.get("/ranking")
def get_ranking():
    rank_file = _data_file(RANK_FILE)
    if not rank_file.exists():
        return []
    df = pd.read_csv(rank_file, sep='\t')
    latest = df.sort_values('timestamp').drop_duplicates(['user_name', 'scenario_name', 'period'], keep='last')
    score_columns = ["total_score", "flood_damage_score", "crop_production_score", "ecosystem_score"]
    for col in score_columns:
        if col not in latest.columns:
            latest[col] = 0.0
    # MayFest 2026: ranking tie-breaks by total, flood, crop, then ecosystem score.
    rank_df = (
        latest.groupby('user_name')[score_columns]
        .mean()
        .reset_index()
        .sort_values(score_columns, ascending=[False, False, False, False])
        .reset_index(drop=True)
    )
    rank_df['rank'] = rank_df.index + 1
    return rank_df.to_dict(orient='records')

@app.post("/compare", response_model=CompareResponse)
def compare_scenario_data(req: CompareRequest):
    selected_data = {name: scenarios_data[name] for name in req.scenario_names if name in scenarios_data}
    if not selected_data:
        raise HTTPException(status_code=404, detail="No scenarios found for given names.")
    indicators_result = {name: calculate_scenario_indicators(df) for name, df in selected_data.items()}
    return CompareResponse(message="Comparison results", comparison=indicators_result)

@app.get("/scenarios")
def list_scenarios():
    return {"scenarios": list(scenarios_data.keys())}

@app.get("/export/{scenario_name}")
def export_scenario_data(scenario_name: str):
    if scenario_name not in scenarios_data:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return scenarios_data[scenario_name].to_csv(index=False)

@app.get("/block_scores")
def get_block_scores():
    rank_file = _data_file(RANK_FILE)
    if not rank_file.exists():
        return []
    try:
        df = pd.read_csv(rank_file, sep="\t")
        df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
        return _json_safe(df.to_dict(orient="records"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/comparison-results")
def get_comparison_results():
    if not COMPARISON_RESULTS_FILE.exists():
        return []
    try:
        df = pd.read_csv(COMPARISON_RESULTS_FILE, sep="\t")
        df = df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)
        return _json_safe(df.to_dict(orient="records"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/comparison-results")
def save_comparison_result(result: Dict[str, Any] = Body(...)):
    required = [
        "user_name",
        "total_score",
        "flood_damage_score",
        "crop_production_score",
        "ecosystem_score",
    ]
    missing = [key for key in required if key not in result]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing)}")

    COMPARISON_RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "user_name": str(result.get("user_name") or "Guest"),
        "mode": str(result.get("mode") or ""),
        # MayFest 2026: ranking uses the three radar scores and their simple average.
        "total_score": float(result.get("total_score") or 0),
        "flood_damage_score": float(result.get("flood_damage_score") or 0),
        "crop_production_score": float(result.get("crop_production_score") or 0),
        "ecosystem_score": float(result.get("ecosystem_score") or 0),
        "metrics_2050": _json_safe(result.get("metrics_2050") or {}),
        "metrics_2075": _json_safe(result.get("metrics_2075") or {}),
        "metrics_2100": _json_safe(result.get("metrics_2100") or {}),
        "scores_2050": _json_safe(result.get("scores_2050") or {}),
        "scores_2075": _json_safe(result.get("scores_2075") or {}),
        "scores_2100": _json_safe(result.get("scores_2100") or {}),
        "turn_1_policy_points": _json_safe(result.get("turn_1_policy_points") or {}),
        "turn_2_policy_points": _json_safe(result.get("turn_2_policy_points") or {}),
        "turn_3_policy_points": _json_safe(result.get("turn_3_policy_points") or {}),
        "timestamp": pd.Timestamp.utcnow(),
    }

    new_df = pd.DataFrame([row])
    if COMPARISON_RESULTS_FILE.exists():
        old_df = pd.read_csv(COMPARISON_RESULTS_FILE, sep="\t")
        old_df = old_df[old_df["user_name"] != row["user_name"]]
        new_df = pd.concat([old_df, new_df], ignore_index=True)
    new_df.to_csv(COMPARISON_RESULTS_FILE, sep="\t", index=False)
    return {"status": "ok"}


@app.get("/baseline-simulation")
def get_baseline_simulation(rcp_value: float = 4.5):
    params = DEFAULT_PARAMS.copy()
    available_rcp_values = list(rcp_climate_params.keys())
    closest_rcp = min(available_rcp_values, key=lambda x: abs(x - rcp_value))
    params.update(rcp_climate_params[closest_rcp])

    initial_values = {
        "temp": 15.5,
        "precip": 1700.0,
        "municipal_demand": 100.0,
        "available_water": 2000.0,
        "crop_yield": 4500.0,
        "hot_days": 30.0,
        "extreme_precip_freq": 0.1,
        "ecosystem_level": 1000.0,
        "levee_level": 0.0,
        "high_temp_tolerance_level": 0.0,
        "forest_area": 5000.0,
        "planting_history": {},
        "urban_level": 0.0,
        "resident_capacity": 0.0,
        "transportation_level": 100.0,
        "levee_investment_total": 0.0,
        "RnD_investment_total": 0.0,
        "risky_house_total": 10000.0,
        "non_risky_house_total": 0.0,
        "resident_burden": 0.0,
        "biodiversity_level": 0.0,
        "paddy_dam_area": 0.0,
    }
    zero_decision = {
        "year": params["start_year"],
        "cp_climate_params": closest_rcp,
        "planting_trees_amount": 0.0,
        "house_migration_amount": 0.0,
        "dam_levee_construction_cost": 0.0,
        "paddy_dam_construction_cost": 0.0,
        "capacity_building_cost": 0.0,
        "transportation_invest": 0.0,
        "agricultural_RnD_cost": 0.0,
    }

    data = simulate_simulation(
        years=params["years"],
        initial_values=initial_values,
        decision_vars_list=[zero_decision],
        params=params,
        fixed_seed=True,
    )
    return _json_safe({"scenario_name": "baseline_no_policy", "data": data})


@app.post("/intermediate-evaluation", response_model=IntermediateEvaluationResponse)
def create_intermediate_evaluation(req: IntermediateEvaluationRequest):
    try:
        return generate_intermediate_evaluation(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/resident-council", response_model=ResidentCouncilResponse)
def create_resident_council(req: IntermediateEvaluationRequest):
    try:
        return generate_resident_council(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/resident-interview", response_model=ResidentInterviewResponse)
def create_resident_interview(req: ResidentInterviewRequest):
    try:
        return generate_resident_interview(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# サーバに送信されているログをWebSocketで受信。現在はbackendに保存中
@app.post("/final-commentary")
def create_final_commentary(results: List[Dict[str, Any]] = Body(...)):
    if not results:
        raise HTTPException(status_code=400, detail="No simulation results provided.")
    return generate_ai_commentary(results)


@app.websocket("/ws/log")
async def websocket_log_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_path = Path(__file__).parent / "data" / "user_log.json"
    import json

    # 既存のログファイルを読み込む（なければ空リスト）
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    else:
        logs = []

    while True:
        try:
            data = await websocket.receive_text()
            # 受信データをJSONとしてパース
            try:
                log_obj = json.loads(data)
            except Exception:
                log_obj = {"raw": data}
            logs.append(log_obj)
            # ファイルに全件書き込み
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
