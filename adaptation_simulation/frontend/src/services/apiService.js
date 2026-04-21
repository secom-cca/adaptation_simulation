// API服务层
import axios from 'axios';
import { BACKEND_URL } from '../config/appConfig';

// 创建axios实例
const apiClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API服务类
export class ApiService {
  // 获取排名数据
  static async fetchRanking() {
    const response = await apiClient.get('/analysis/ranking');
    return response.data;
  }

  // 获取评分数据
  static async fetchBlockScores() {
    const response = await apiClient.get('/analysis/block_scores');
    return response.data;
  }

  // 运行仿真
  static async runSimulation(simulationData) {
    const response = await apiClient.post('/simulation/run', simulationData);
    return response.data;
  }

  // 获取情景列表
  static async fetchScenarios() {
    const response = await apiClient.get('/simulation/scenarios');
    return response.data;
  }

  // 比较情景
  static async compareScenarios(compareData) {
    const response = await apiClient.post('/analysis/compare', compareData);
    return response.data;
  }

  // 导出情景数据
  static async exportScenario(scenarioName) {
    const response = await apiClient.get(`/simulation/export/${scenarioName}`);
    return response.data;
  }
}

export default ApiService;
