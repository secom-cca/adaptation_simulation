"""
Simulation API Routes
"""
from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from typing import Dict

from ..models.models import SimulationRequest, SimulationResponse
from ..core.config import DEFAULT_PARAMS, rcp_climate_params
from ..core.simulation import simulate_simulation
from ..utils.utils import aggregate_blocks
from ..config import settings

router = APIRouter(prefix="/simulation", tags=["simulation"])

# 存储仿真数据
scenarios_data: Dict[str, pd.DataFrame] = {}

@router.post("/run", response_model=SimulationResponse)
def run_simulation(req: SimulationRequest):
    """运行仿真"""
    scenario_name = req.scenario_name
    mode = req.mode
    decision_df = pd.DataFrame([dv.model_dump() for dv in req.decision_vars]) if req.decision_vars else pd.DataFrame()

    # 更新参数基于RCP情景和当前值
    params = DEFAULT_PARAMS.copy()
    rcp_param = rcp_climate_params.get(req.decision_vars[0].cp_climate_params, {})
    params.update(rcp_param)

    all_df = pd.DataFrame()
    block_scores = []

    if mode == "Monte Carlo Simulation Mode":
        results = []
        for sim in range(req.num_simulations):
            sim_result = simulate_simulation(
                years=params['years'],
                initial_values=req.current_year_index_seq.model_dump(),
                decision_vars_list=decision_df,
                params=params
            )
            df_sim = pd.DataFrame(sim_result)
            df_sim["Simulation"] = sim
            results.append(df_sim)
        all_df = pd.concat(results, ignore_index=True)
        block_scores = []

    elif mode == "Sequential Decision-Making Mode":
        sim_years = np.arange(req.decision_vars[0].year, req.decision_vars[0].year + 1)
        result = simulate_simulation(
            years=sim_years,
            initial_values=req.current_year_index_seq.model_dump(),
            decision_vars_list=decision_df,
            params=params
        )
        all_df = pd.DataFrame(result)
        block_scores = aggregate_blocks(all_df)

        # 保存日志
        _save_simulation_logs(req, scenario_name, block_scores)

    elif mode == "Predict Simulation Mode":
        # 全期间的预测值计算
        params = DEFAULT_PARAMS.copy()
        sim_years = np.arange(req.decision_vars[0].year, params['end_year'] + 1)
        seq_result = simulate_simulation(
            years=sim_years,
            initial_values=req.current_year_index_seq.model_dump(),
            decision_vars_list=decision_df,
            params=params
        )
        all_df = pd.DataFrame(seq_result)
        block_scores = []

    elif mode == "Record Results Mode":
        _copy_results_to_frontend()

    else:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")

    if mode != "Predict Simulation Mode":
        scenarios_data[scenario_name] = all_df.copy()

    return SimulationResponse(
        scenario_name=scenario_name,
        data=all_df.to_dict(orient="records"),
        block_scores=block_scores
    )

def _save_simulation_logs(req: SimulationRequest, scenario_name: str, block_scores: list):
    """保存仿真日志"""
    # 保存决策日志
    df_log = pd.DataFrame([dv.model_dump() for dv in req.decision_vars])
    df_log['user_name'] = req.user_name
    df_log['scenario_name'] = scenario_name
    df_log['timestamp'] = pd.Timestamp.utcnow()
    
    if settings.ACTION_LOG_FILE.exists():
        df_old = pd.read_csv(settings.ACTION_LOG_FILE)
        df_combined = pd.concat([df_old, df_log], ignore_index=True)
    else:
        df_combined = df_log
    df_combined.to_csv(settings.ACTION_LOG_FILE, index=False)

    # 保存评分数据
    df_csv = pd.DataFrame(block_scores)
    df_csv['user_name'] = req.user_name
    df_csv['scenario_name'] = scenario_name
    df_csv['timestamp'] = pd.Timestamp.utcnow()
    df_csv['user_name'].to_csv(settings.YOUR_NAME_FILE, index=False)
    
    if settings.RANK_FILE.exists():
        old = pd.read_csv(settings.RANK_FILE, sep='\t')
        merged = (
            old.set_index(['user_name', 'scenario_name', 'period'])
            .combine_first(df_csv.set_index(['user_name', 'scenario_name', 'period']))
            .reset_index()
        )
        merged.to_csv(settings.RANK_FILE, sep='\t', index=False)
    else:
        df_csv.to_csv(settings.RANK_FILE, sep='\t', index=False)

def _copy_results_to_frontend():
    """复制结果到前端目录"""
    import shutil
    import glob
    from pathlib import Path

    src_dir = settings.DATA_DIR
    dst_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "results" / "data"
    dst_dir.mkdir(parents=True, exist_ok=True)

    for filepath in glob.glob(str(src_dir / "*.csv")) + glob.glob(str(src_dir / "*.tsv")):
        shutil.copy(filepath, dst_dir)

@router.get("/scenarios")
def list_scenarios():
    """获取所有情景列表"""
    return {"scenarios": list(scenarios_data.keys())}

@router.get("/export/{scenario_name}")
def export_scenario_data(scenario_name: str):
    """导出情景数据"""
    if scenario_name not in scenarios_data:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return scenarios_data[scenario_name].to_csv(index=False)
