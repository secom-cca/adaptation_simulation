// 应用配置

// 后端API配置
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

// WebSocket配置
export const WEBSOCKET_LOG_URL = "ws://localhost:8000/ws/log";
export const WEBSOCKET_REALSENSE_URL = "ws://localhost:3001";

// 默认值配置
export const DEFAULT_DECISION_VAR = {
  year: 2026,
  planting_trees_amount: 0.,   // 植林・森林保全
  house_migration_amount: 0.,  // 住宅移転・嵩上げ
  dam_levee_construction_cost: 0., //ダム・堤防工事
  paddy_dam_construction_cost: 0., //田んぼダム工事
  capacity_building_cost: 0.,   // 防災訓練・普及啓発
  transportation_invest: 0,     // 交通網の拡充
  agricultural_RnD_cost: 0,      // 農業研究開発
  cp_climate_params: 4.5 //RCPの不確実性シナリオ
};

export const DEFAULT_CURRENT_VALUES = {
  temp: 15,
  precip: 1700,
  municipal_demand: 100,
  available_water: 1000,
  crop_yield: 100,
  hot_days: 30,
  extreme_precip_freq: 0.1,
  ecosystem_level: 100,
  levee_level: 0.5,
  high_temp_tolerance_level: 0,
  forest_area: 0,
  planting_history: {},
  urban_level: 100,
  resident_capacity: 0,
  transportation_level: 0,
  levee_investment_total: 0,
  RnD_investment_total: 0,
  risky_house_total: 10000,
  non_risky_house_total: 0,
  resident_burden: 5.379 * 10**8,
  biodiversity_level: 100,
};

// 本地存储键名
export const STORAGE_KEYS = {
  USER_NAME: 'userName',
  SELECTED_MODE: 'selectedMode',
  CHART_PREDICT_MODE: 'chartPredictMode',
  LANGUAGE: 'language'
};

// 应用模式
export const APP_MODES = {
  GROUP: 'group',
  UPSTREAM: 'upstream',
  DOWNSTREAM: 'downstream'
};

// 图表预测模式
export const CHART_PREDICT_MODES = {
  BEST_WORST: 'best-worst',
  MONTE_CARLO: 'monte-carlo',
  NONE: 'none'
};

// 语言选项
export const LANGUAGES = {
  JAPANESE: 'ja',
  ENGLISH: 'en'
};
