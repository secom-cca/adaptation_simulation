"""
Analysis and Comparison API Routes
"""
from fastapi import APIRouter, HTTPException
import pandas as pd

from ..models.models import CompareRequest, CompareResponse
from ..utils.utils import calculate_scenario_indicators
from ..config import settings

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/compare", response_model=CompareResponse)
def compare_scenario_data(req: CompareRequest):
    """比较情景数据"""
    from ..routers.simulation import scenarios_data
    
    selected_data = {name: scenarios_data[name] for name in req.scenario_names if name in scenarios_data}
    if not selected_data:
        raise HTTPException(status_code=404, detail="No scenarios found for given names.")
    
    indicators_result = {name: calculate_scenario_indicators(df) for name, df in selected_data.items()}
    return CompareResponse(message="Comparison results", comparison=indicators_result)

@router.get("/ranking")
def get_ranking():
    """获取排名数据"""
    if not settings.RANK_FILE.exists():
        return []
    
    df = pd.read_csv(settings.RANK_FILE, sep='\t')
    latest = df.sort_values('timestamp').drop_duplicates(['user_name', 'scenario_name', 'period'], keep='last')
    rank_df = (
        latest.groupby('user_name')['total_score']
        .mean()
        .reset_index()
        .sort_values('total_score', ascending=False)
        .reset_index(drop=True)
    )
    rank_df['rank'] = rank_df.index + 1
    return rank_df.to_dict(orient='records')

@router.get("/block_scores")
def get_block_scores():
    """获取区块评分数据"""
    if not settings.RANK_FILE.exists():
        return []
    
    try:
        df = pd.read_csv(settings.RANK_FILE, sep="\t")
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
