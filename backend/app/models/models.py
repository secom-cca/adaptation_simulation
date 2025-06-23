"""
Data Models for Climate Adaptation Simulation API
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class DecisionVar(BaseModel):
    year: int
    planting_trees_amount: float = 0.0
    house_migration_amount: float = 0.0
    dam_levee_construction_cost: float = 0.0
    paddy_dam_construction_cost: float = 0.0
    capacity_building_cost: float = 0.0
    transportation_invest: float = 0.0
    agricultural_RnD_cost: float = 0.0
    cp_climate_params: float = 4.5

class CurrentValues(BaseModel):
    temp: float = 15.0
    precip: float = 1700.0
    municipal_demand: float = 100.0
    available_water: float = 1000.0
    crop_yield: float = 100.0
    hot_days: float = 30.0
    extreme_precip_freq: float = 0.1
    ecosystem_level: float = 100.0
    levee_level: float = 0.5
    high_temp_tolerance_level: float = 0.0
    forest_area: float = 0.0
    planting_history: Dict[str, Any] = {}
    urban_level: float = 100.0
    resident_capacity: float = 0.0
    transportation_level: float = 0.0
    levee_investment_total: float = 0.0
    RnD_investment_total: float = 0.0
    risky_house_total: float = 10000.0
    non_risky_house_total: float = 0.0
    resident_burden: float = 5.379e8
    biodiversity_level: float = 100.0

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
    # 添加仿真数据字段，用于Record Results Mode
    simulation_data: Optional[List[Dict[str, Any]]] = []
    result_history: Optional[List[Dict[str, Any]]] = []

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
