from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DecisionVar(BaseModel):
    year: int
    planting_trees_amount: float
    house_migration_amount: float
    dam_levee_construction_cost: float
    paddy_dam_construction_cost: float
    capacity_building_cost: float
    transportation_invest: float
    agricultural_RnD_cost: float
    cp_climate_params: float

class CurrentValues(BaseModel):
    temp: float
    precip: float
    municipal_demand: float
    available_water: float
    crop_yield: float
    hot_days: float
    extreme_precip_freq: float
    ecosystem_level: float
    levee_level: Optional[float] = 0.0
    high_temp_tolerance_level: Optional[float] = 0.0
    forest_area: Optional[float] = 0.0
    planting_history: Optional[Dict[int, float]] = {}
    urban_level: Optional[float] = 0.0
    resident_capacity: Optional[float] = 0.0
    transportation_level: Optional[float] = 100.0
    levee_investment_total: Optional[float] = 0.0
    RnD_investment_total: Optional[float] = 0.0
    risky_house_total: Optional[float] = 10000.0
    non_risky_house_total: Optional[float] = 0.0
    resident_burden: Optional[float] = 0.0
    biodiversity_level: Optional[float] = 0.0
    paddy_dam_area: float = 0.0

class BlockRaw(BaseModel):
    period: str
    raw: Dict[str, float]
    score: Dict[str, float]
    total_score: float

class SimulationRequest(BaseModel):
    user_name: str
    scenario_name: str
    mode: str
    decision_vars: List[DecisionVar] = []
    num_simulations: int = 100
    current_year_index_seq: CurrentValues

class SimulationResponse(BaseModel):
    scenario_name: str
    data: List[Dict[str, Any]]
    block_scores: List[BlockRaw]

class CompareRequest(BaseModel):
    scenario_names: List[str]
    variables: List[str]

class CompareResponse(BaseModel):
    message: str
    comparison: Dict[str, Any]
