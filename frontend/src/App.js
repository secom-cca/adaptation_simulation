import React, { useState, useRef, useEffect } from "react";
import { Box, Button, Dialog, DialogTitle, DialogContent, FormControl, Grid, IconButton, InputLabel, MenuItem, Slider, Stack, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Paper, TextField } from '@mui/material';
import { LineChart, ScatterChart, Gauge } from '@mui/x-charts';
import { Agriculture, Biotech, EmojiTransportation, Flood, Forest, Houseboat, LocalLibrary, PlayCircle } from '@mui/icons-material';
import InfoIcon from '@mui/icons-material/Info';
import SettingsIcon from '@mui/icons-material/Settings';
import axios from "axios";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import ModelExplanationPage from "./ModelExplanationPage"; // 模型解释页面
import ThankYouPage from "./ThankYouPage"; // Thank You页面

// ※ chart.js v4 の設定
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

// バックエンドの URL を環境変数や直書きなどで指定
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://web-production-5fb04.up.railway.app";

// 各種設定

const getLineChartIndicators = (language) => {
  const indicators = {
    ja: {
      'Flood Damage': { labelTitle: '洪水被害', max: 20000, min: 0, unit: '万円' },
      'Crop Yield': { labelTitle: '収穫量', max: 5, min: 0, unit: 'ton/ha' },
      'Ecosystem Level': { labelTitle: '生態系', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: '予算', max: 100000, min: 0, unit: '万円' },
      'Temperature (℃)': { labelTitle: '【気候要素】年平均気温', max: 20, min: 12, unit: '℃' },
      'Precipitation (mm)': { labelTitle: '【気候要素】年降水量', max: 3000, min: 0, unit: 'mm' },
      'Available Water': { labelTitle: '【中間要素】利用可能な水量', max: 3000, min: 0, unit: 'mm' }
    },
    en: {
      'Flood Damage': { labelTitle: 'Flood Damage', max: 20000, min: 0, unit: '10k yen' },
      'Crop Yield': { labelTitle: 'Crop Yield', max: 5, min: 0, unit: 'ton/ha' },
      'Ecosystem Level': { labelTitle: 'Ecosystem Level', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: 'Municipal Cost', max: 100000, min: 0, unit: '10k yen' },
      'Temperature (℃)': { labelTitle: '[Climate Factor] Average Temperature', max: 20, min: 12, unit: '°C' },
      'Precipitation (mm)': { labelTitle: '[Climate Factor] Annual Precipitation', max: 3000, min: 0, unit: 'mm' },
      'Available Water': { labelTitle: '[Intermediate Factor] Available Water', max: 3000, min: 0, unit: 'mm' }
    }
  };
  return indicators[language] || indicators.ja;
};

const SIMULATION_YEARS = 25 // 一回のシミュレーションで進める年数を決定する 
const LINE_CHART_DISPLAY_INTERVAL = 100 // ms
const INDICATOR_CONVERSION = {
  'Municipal Cost': 1 / 10000, // 円 → 億円
  'Flood Damage': 1 / 10000, // 円 → 万円
  'Crop Yield': 1 / 1000 // kg → ton（例）
};

// 日本語と英語のテキスト定義
const texts = {
  ja: {
    title: '気候変動適応策検討シミュレーション',
    cycle: 'サイクル',
    year: '年',
    cropYield: '収穫量',
    floodDamage: '洪水被害',
    ecosystemLevel: '生態系',
    municipalCost: '予算',
    temperature: '年平均気温',
    precipitation: '年降水量',
    availableWater: '利用可能な水量',
    unit: {
      tonHa: 'ton/ha',
      manYen: '万円',
      none: '-',
      celsius: '℃',
      mm: 'mm',
      frequency: '回/年'
    },
    mode: {
      group: '（１）グループモード',
      upstream: '（２）上流モード',
      downstream: '（３）下流モード',
      groupDesc: '全ての項目を操作可能',
      upstreamDesc: '植林・河川堤防・田んぼダムのみ',
      downstreamDesc: '田んぼダム・住宅移転・防災訓練のみ'
    },
    predictMode: {
      bestWorst: 'モード（１）：ベストケース・ワーストケース',
      monteCarlo: 'モード（２）：モンテカルロシミュレーション（10回）',
      none: 'モード（３）：予測結果を表示しない'
    },
    settings: {
      title: '設定',
      predictDataMode: '折れ線グラフの予測データ表示モード',
      languageMode: '言語設定',
      close: '閉じる'
    },
    dialog: {
      nameTitle: 'お名前とモードを入力してください',
      nameLabel: 'お名前',
      modeTitle: 'モードを選択してください',
      register: '登録',
      nameError: 'この名前は既に使用されています。別の名前を入力してください。'
    },
    sliders: {
      plantingTrees: '植林・森林保全',
      damLevee: '河川堤防',
      agriculturalRnD: '高温耐性品種',
      houseMigration: '住宅移転',
      paddyDam: '田んぼダム',
      capacityBuilding: '防災訓練・啓発'
    },
    chart: {
      measuredValue: '実測値',
      upperLimit: '上限値予測',
      lowerLimit: '下限値予測',
      monteCarlo: 'モンテカルロ',
      selectYAxis: '縦軸を選択',
      years: 'Years',
      weatherCondition: '年の気象条件と将来影響予測',
      averageTemp: '年平均気温',
      annualPrecip: '年降水量',
      heavyRainFreq: '大雨の頻度',
      residentBurden: '住民の負担',
      biodiversity: '生物多様性',
      frequency: '回/年'
    },
    buttons: {
      advanceYears: '25年進める',
      inputComplete: '回の入力完了',
      nextCycle: '次のサイクル (',
      startNext: ') を開始',
      cycleComplete: 'サイクル',
      completed: 'が完了しました！',
      // viewResults: '結果を見る',
    },
    rcp: {
      scenario: 'RCPシナリオ'
    },
    scatter: {
      title: 'サイクルの比較',
      description: '各サイクルを比較',
      xAxis: 'X軸',
      yAxis: 'Y軸',
      plotAttribute: 'プロット属性',
      average: '平均値',
      year2050: '2050年',
      year2075: '2075年', 
      year2100: '2100年',
      allDisplay: '全て表示',
      markerSize: 'マーカーサイズと透明度（時点）:',
      small: '2050年',
      medium: '2075年',
      large: '2100年',
      cycleColor: 'サイクルの色:',
      inputHistory: '各サイクルの入力履歴',
      cycle: 'サイクル',
      inputCount: '入力回数',
      inputYear: '入力年',
      noCompletedCycles: '完了したサイクルがありません。サイクルが完了すると結果が表示されます。',
      historyFilter: 'フィルター',
      historySort: 'ソート',
      filterAll: 'すべて',
      filterCycle1: 'サイクル1',
      filterCycle2: 'サイクル2',
      filterCycle3: 'サイクル3',
      sortByCycle: 'サイクル順',
      sortByYear: '年順',
      sortByInput: '入力回数順',
      yearFilter: '年次選択',
      cycleFilter: 'サイクル選択',
      allYears: 'すべての年次',
      allCycles: 'すべてのサイクル'
    }
  },
  en: {
    title: 'Climate Change Adaptation Strategy Simulation',
    cycle: 'Cycle',
    year: 'Year',
    cropYield: 'Crop Yield',
    floodDamage: 'Flood Damage',
    ecosystemLevel: 'Ecosystem Level',
    municipalCost: 'Municipal Cost',
    temperature: 'Average Temperature',
    precipitation: 'Annual Precipitation',
    availableWater: 'Available Water',
    unit: {
      tonHa: 'ton/ha',
      manYen: '10k yen',
      none: '-',
      celsius: '°C',
      mm: 'mm',
      frequency: 'times/year'
    },
    mode: {
      group: '(1) Group Mode',
      upstream: '(2) Upstream Mode',
      downstream: '(3) Downstream Mode',
      groupDesc: 'All items can be operated',
      upstreamDesc: 'Forest conservation, river levee, paddy dam only',
      downstreamDesc: 'Paddy dam, house migration, disaster training only'
    },
    predictMode: {
      bestWorst: 'Mode (1): Best Case - Worst Case',
      monteCarlo: 'Mode (2): Monte Carlo Simulation (10 times)',
      none: 'Mode (3): No prediction display'
    },
    settings: {
      title: 'Settings',
      predictDataMode: 'Line Chart Prediction Data Display Mode',
      languageMode: 'Language Settings',
      close: 'Close'
    },
    dialog: {
      nameTitle: 'Enter your name and select mode',
      nameLabel: 'Name',
      modeTitle: 'Please select a mode',
      register: 'Register',
      nameError: 'This name is already in use. Please enter a different name.'
    },
    sliders: {
      plantingTrees: 'Forest Conservation',
      damLevee: 'River Levee',
      agriculturalRnD: 'Heat-resistant Varieties',
      houseMigration: 'House Migration',
      paddyDam: 'Paddy Dam',
      capacityBuilding: 'Disaster Training'
    },
    chart: {
      measuredValue: 'Measured Value',
      upperLimit: 'Upper Limit Prediction',
      lowerLimit: 'Lower Limit Prediction',
      monteCarlo: 'Monte Carlo',
      selectYAxis: 'Select Y-axis',
      years: 'Years',
      weatherCondition: 'Weather Conditions and Future Impact Predictions',
      averageTemp: 'Average Temperature',
      annualPrecip: 'Annual Precipitation',
      heavyRainFreq: 'Heavy Rain Frequency',
      residentBurden: 'Resident Burden',
      biodiversity: 'Biodiversity',
      frequency: 'times/year'
    },
    buttons: {
      advanceYears: '25 years advance',
      inputComplete: 'inputs completed',
      nextCycle: 'Next Cycle (',
      startNext: ') Start',
      cycleComplete: 'Cycle',
      completed: 'completed!',
      // viewResults: 'View Results',
    },
    rcp: {
      scenario: 'RCP Scenario'
    },
    scatter: {
      title: 'Cycle Comparison',
      description: 'Compare cycles',
      xAxis: 'X-axis',
      yAxis: 'Y-axis',
      plotAttribute: 'Plot Attribute',
      average: 'Average',
      year2050: '2050',
      year2075: '2075',
      year2100: '2100',
      allDisplay: 'All',
      markerSize: 'Marker Size and Opacity (Time Point):',
      small: '2050',
      medium: '2075',
      large: '2100',
      cycleColor: 'Cycle Color:',
      inputHistory: 'Input History for Each Cycle',
      cycle: 'Cycle',
      inputCount: 'Input Count',
      inputYear: 'Input Year',
      noCompletedCycles: 'No completed cycles. Results will be displayed when cycles are completed.',
      historyFilter: 'Filter',
      historySort: 'Sort',
      filterAll: 'All',
      filterCycle1: 'Cycle 1',
      filterCycle2: 'Cycle 2',
      filterCycle3: 'Cycle 3',
      sortByCycle: 'By Cycle',
      sortByYear: 'By Year',
      sortByInput: 'By Input Count',
      yearFilter: 'Year Selection',
      cycleFilter: 'Cycle Selection',
      allYears: 'All Years',
      allCycles: 'All Cycles'
    }
  }
};

function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/formula" element={<ModelExplanationPage />} />
        <Route path="/thank-you" element={<ThankYouPage />} />
      </Routes>
    </Router>
  );
}

function App() {
  // シミュレーション実行用のステート
  const [scenarioName, setScenarioName] = useState("シナリオ1");
  const [numSimulations, setNumSimulations] = useState(1);
  const isRunningRef = useRef(false);
  const [chartPredictData, setChartPredictData] = useState([[], []]); // [0]が初期値予測 [1]が下限値予測、[2]が上限値予測
  const [resultHistory, setResultHistory] = useState([]); // サイクルごとの結果履歴
  const [currentCycle, setCurrentCycle] = useState(1); // 現在のサイクル番号
  const [cycleCompleted, setCycleCompleted] = useState(false); // サイクル完了フラグ
  const [inputCount, setInputCount] = useState(0); // 現在のサイクルでの入力回数（0-3回）
  const [inputHistory, setInputHistory] = useState([]); // 現在のサイクルでの入力履歴
  const [openResultUI, setOpenResultUI] = useState(false);
  const [openSettingsDialog, setOpenSettingsDialog] = useState(false); // 設定ダイアログ
  const [selectedXAxis, setSelectedXAxis] = useState('Crop Yield'); // 散布図X軸選択
  const [selectedYAxis, setSelectedYAxis] = useState('Flood Damage'); // 散布図Y軸選択
  const [selectedPlotAttribute, setSelectedPlotAttribute] = useState('average'); // プロット属性選択: 'average', '2050', '2075', '2100', 'all'
  const [selectedHistoryFilter, setSelectedHistoryFilter] = useState('all'); // 入力履歴フィルター選択
  const [selectedHistorySort, setSelectedHistorySort] = useState('cycle'); // 入力履歴ソート選択
  const [selectedYearFilter, setSelectedYearFilter] = useState('all'); // 年次フィルター選択
  const [selectedCycleFilter, setSelectedCycleFilter] = useState('all'); // サイクルフィルター選択
  const [chartPredictMode, setChartPredictMode] = useState(localStorage.getItem('chartPredictMode') || 'monte-carlo'); // 予測データ表示モード: 'best-worst', 'monte-carlo', 'none'
  const [language, setLanguage] = useState(localStorage.getItem('language') || 'ja'); // 言語モード: 'ja', 'en'
  const [decisionVar, setDecisionVar] = useState({
    year: 2026,
    planting_trees_amount: 0.,   // 植林・森林保全
    house_migration_amount: 0.,  // 住宅移転・嵩上げ
    dam_levee_construction_cost: 0., //ダム・堤防工事
    paddy_dam_construction_cost: 0., //田んぼダム工事
    capacity_building_cost: 0.,   // 防災訓練・普及啓発
    // irrigation_water_amount: 100, // 灌漑水量
    // released_water_amount: 100,   // 放流水量
    transportation_invest: 0,     // 交通網の拡充
    agricultural_RnD_cost: 0,      // 農業研究開発
    cp_climate_params: 4.5 //RCPの不確実性シナリオ
  })
  const [currentValues, setCurrentValues] = useState({
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
  })
  const [simulationData, setSimulationData] = useState([]); // 結果格納

  // ロード中やエラー表示用
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // リアルタイム更新用
  const currentValuesRef = useRef(currentValues);
  const decisionVarRef = useRef(decisionVar);
  const simulationDataRef = useRef(simulationData);

  // LineChartの縦軸の変更
  const [selectedIndicator, setSelectedIndicator] = useState('Flood Damage');
  const currentIndicator = getLineChartIndicators(language)[selectedIndicator];
  const handleLineChartChange = (event) => {
    setSelectedIndicator(event.target.value);

    // --- 縦軸選択変更ログを队列に追加 ---
    addLogToQueue({
      type: "GraphSelect",
      name: event.target.value
    });
    console.log(`📊 图表Y轴选择: ${event.target.value}`);
  };

  const [userName, setUserName] = useState(localStorage.getItem('userName') || '');
  const [openNameDialog, setOpenNameDialog] = useState(!userName);
  const [blockScores, setBlockScores] = useState([]);   // Array<Backend BlockRaw>
  const [ranking,setRanking] = useState([]);
  const [showResultButton, setShowResultButton] = useState(false);
  const [userNameError, setUserNameError] = useState("")
  const [selectedMode, setSelectedMode] = useState(localStorage.getItem('selectedMode') || 'group'); // モード選択: 'group', 'upstream', 'downstream'

  // ここでuseRefを定義
  const wsLogRef = useRef(null);
  const [logQueue, setLogQueue] = useState([]); // 前端log缓存队列
  const [logStatus, setLogStatus] = useState('disconnected'); // WebSocket连接状态

  // 结束实验功能
  const handleEndExperiment = async () => {
    try {
      // 发送结束实验日志到队列
      addLogToQueue({
        type: "EndExperiment",
        name: userName,
        timestamp: new Date().toISOString()
      });

      // 立即发送所有队列中的日志
      await sendLogQueue();

      // 发送用户行为数据到后端
      const allUserLogs = [...logQueue];
      if (allUserLogs.length > 0) {
        await axios.post(`${BACKEND_URL}/experiment/end`, {
          user_name: userName,
          logs: allUserLogs
        });
      }

      // 跳转到Thank You页面
      window.location.href = `/thank-you?user=${encodeURIComponent(userName)}`;
    } catch (error) {
      console.error('结束实验失败:', error);
      alert('实验结束时发生错误，请重试');
    }
  };

  // 添加log到队列的函数
  const addLogToQueue = (logData) => {
    const timestamp = new Date().toISOString();
    const logEntry = {
      ...logData,
      timestamp,
      user_name: userName,
      mode: chartPredictMode
    };

    setLogQueue(prev => [...prev, logEntry]);
    console.log(`📝 Log添加到队列: ${logData.type} - ${logData.name || ''}`);
  };

  // 发送log队列到后端
  const sendLogQueue = async () => {
    if (logQueue.length === 0) return;

    try {
      const response = await axios.post(`${BACKEND_URL}/logs/batch`, {
        logs: logQueue
      });

      if (response.status === 200) {
        console.log(`✅ 成功发送 ${logQueue.length} 条log到后端`);
        setLogQueue([]); // 清空队列
      }
    } catch (error) {
      console.error(`❌ 发送log失败:`, error);
      console.log(`📦 保留 ${logQueue.length} 条log在队列中，等待下次发送`);
    }
  };

  // 每5秒发送一次log队列
  useEffect(() => {
    const interval = setInterval(sendLogQueue, 5000);
    return () => clearInterval(interval);
  }, [logQueue]);

  // ここでuseEffectを定義
  useEffect(() => {
    wsLogRef.current = new WebSocket("wss://web-production-5fb04.up.railway.app/ws/log");
    wsLogRef.current.onopen = () => {
      console.log("✅ Log WebSocket connected");
      setLogStatus('connected');
    };
    wsLogRef.current.onerror = (e) => {
      console.error("Log WebSocket error", e);
      setLogStatus('error');
    };
    wsLogRef.current.onclose = () => {
      console.log("⚠️ Log WebSocket closed");
      setLogStatus('disconnected');
    };
    return () => {
      wsLogRef.current && wsLogRef.current.close();
    };
  }, []);

  const fetchRanking = async () => {
    const res = await axios.get(`${BACKEND_URL}/ranking`);
    setRanking(res.data);
  };
  const handleUserNameRegister = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/block_scores`); // ここはAPIでCSV読ませる形にする
      const existingUsers = new Set(res.data.map(row => row.user_name));
      
      if (existingUsers.has(userName.trim())) {
        setUserNameError("この名前は既に使用されています。別の名前を入力してください。");
      } else {
        localStorage.setItem('userName', userName.trim());
        localStorage.setItem('selectedMode', selectedMode); // 選択されたモードも保存
        localStorage.setItem('chartPredictMode', chartPredictMode); // 予測モードも保存
        setUserName(userName.trim());
        setOpenNameDialog(false);
        setUserNameError(""); // エラー解除

        // --- ユーザ名登録ログを队列に追加 ---
        addLogToQueue({
          type: "Register",
          name: userName.trim()
        });
        console.log(`👤 用户注册: ${userName.trim()}`);
      }    
    } catch (err) {
      console.error("ユーザー名チェックエラー", err);
    }
  };
  

  useEffect(() => {
    currentValuesRef.current = currentValues;
  }, [currentValues]);

  useEffect(() => {
    decisionVarRef.current = decisionVar;
    fetchForecastData();
  }, [decisionVar]);

  useEffect(() => {
    simulationDataRef.current = simulationData;
  }, [simulationData]);

  useEffect(() => {
    // 每次访问都清除用户名，确保弹窗显示
    localStorage.removeItem('userName');
    localStorage.removeItem('selectedMode');
    localStorage.removeItem('chartPredictMode');
  
    const storedName = localStorage.getItem('userName');
    const storedMode = localStorage.getItem('selectedMode');
    const storedPredictMode = localStorage.getItem('chartPredictMode');
    if (!storedName || storedName.trim() === '') {
      setOpenNameDialog(true);
    } else {
      setUserName(storedName);
      setSelectedMode(storedMode || 'group');
      setChartPredictMode(storedPredictMode || 'monte-carlo');
    }
  }, []);

  useEffect(() => {
    const ws = new WebSocket("wss://web-production-5fb04.up.railway.app/ws");

    ws.onopen = () => {
      console.log("✅ WebSocket connected");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("受信:", data);

      for (const [key, value] of Object.entries(data)) {
        if (key === "simulate" && value === true) {
          handleClickCalc();  // 自動で25年進める
        } else {
          updateDecisionVar(key, value);
        }
      }
    };

    let resetFlag = false;

    ws.onmessage = (event) => {
      if (isRunningRef.current) {
        console.log("🛑 シミュレーション中のため信号を無視");
        return;
      }

      const data = JSON.parse(event.data);
      console.log("受信:", data);

      if (data.simulate_trigger === true) {
        setDecisionVar(prev => ({
          ...prev,
          transportation_invest: 0,
          agricultural_RnD_cost: 0,
          planting_trees_amount: 0,
          house_migration_amount: 0,
          dam_levee_construction_cost: 0,
          paddy_dam_construction_cost: 0,
          capacity_building_cost: 0
        }));
        handleClickCalc();
      } else {
        setDecisionVar(prev => {
          const updated = { ...prev };
          for (const [key, value] of Object.entries(data)) {
            if (typeof prev[key] === "number") {
              const delta = value;
              const increment = {
                transportation_invest: 5,
                agricultural_RnD_cost: 5,
                planting_trees_amount: 100,
                house_migration_amount: 5,
                dam_levee_construction_cost: 1,
                paddy_dam_construction_cost: 5,
                capacity_building_cost: 5,
              }[key] || 1;

              updated[key] = Math.min(delta * increment, increment * 2);
            }
          }
          return updated;
        });
      }
    };

    
    ws.onerror = (err) => {
      console.error("❌ WebSocket error", err);
    };

    ws.onclose = () => {
      console.warn("⚠️ WebSocket closed");
    };

    return () => ws.close();
  }, []);

  // (A) シミュレーション実行ハンドラ
  const handleSimulate = async () => {
    setLoading(true);
    setError("");
    if (!userName || userName.trim() === "") {
      alert("お名前を入力してください");
      setOpenNameDialog(true);
      return;
    }
    try {
      // /simulate に POST するパラメータ
      console.log("現在の入力:", decisionVarRef.current, currentValuesRef.current)
      console.log("RCP value being sent:", decisionVarRef.current.cp_climate_params)
      
      const body = {
        scenario_name: scenarioName,
        user_name: userName,
        mode: "Sequential Decision-Making Mode",  // "Monte Carlo Simulation Mode" または "Sequential Decision-Making Mode"
        decision_vars: [decisionVarRef.current],
        num_simulations: Number(numSimulations),
        current_year_index_seq: currentValuesRef.current
      };

      // axios でリクエスト
      const resp = await axios.post(`${BACKEND_URL}/simulate`, body);
      console.log("API Response:", resp.data.data[0]);
      // resp.data はバックエンドの SimulationResponse (scenario_name, data)
      if (resp.data && resp.data.data) {
        const processedData = processIndicatorData(resp.data.data, selectedIndicator);
        setSimulationData(prev => [...prev, ...processedData]);
        updateCurrentValues(resp.data.data[0])
      }
    } catch (err) {
      console.error('API エラー:', error.response.data);
      setError("シミュレーションに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleClickCalc = async () => {
    // --- 「25年進める」押下ログを队列に追加 ---
    addLogToQueue({
      type: "Next",
      name: decisionVar.year,
      cycle: currentCycle
    });
    console.log(`⏭️ 25年进める按钮点击: 年份${decisionVar.year}, 周期${currentCycle}`);

    if (isRunningRef.current) return;
    isRunningRef.current = true;

    let nextYear = decisionVar.year;
    let count = 0;
    let cycleStartYear = decisionVar.year; // サイクル開始年を記録
    let latestSimulationData = []; // 最新のシミュレーションデータを保存

    // 現在の入力を履歴に記録
    const currentInput = {
      inputNumber: inputCount + 1,
      year: decisionVar.year,
      decisionVariables: { ...decisionVar },
      currentValues: { ...currentValues }
    };
    
    setInputHistory(prev => [...prev, currentInput]);
    setInputCount(prev => prev + 1);

    while (count < SIMULATION_YEARS) {

      // シミュレーション実行
      await handleSimulate();

      // 次へ
      count += 1;
      nextYear += 1;

      // 現在の年を更新
      updateDecisionVar("year", nextYear);

      // 表示更新のために一時停止（見た目をスムーズに）
      await new Promise(res => setTimeout(res, LINE_CHART_DISPLAY_INTERVAL));
    }

    isRunningRef.current = false;
    
    // 3回の入力が完了した場合、サイクル完了処理
    if (inputCount >= 2) { // 0ベースなので2で3回目
      // 最新のsimulationDataを取得
      latestSimulationData = [...simulationDataRef.current];
      
      // サイクルの結果をresultHistoryに保存
      const cycleResult = {
        cycleNumber: currentCycle,
        startYear: cycleStartYear,
        endYear: 2100,
        inputHistory: [...inputHistory, currentInput], // 全3回の入力を含む
        finalValues: { ...currentValues },
        simulationData: latestSimulationData // 最新のシミュレーションデータを使用
      };
      
      setResultHistory(prev => [...prev, cycleResult]);
      setCycleCompleted(true);
      setShowResultButton(true);
    }
    
  };

  // decisionVarが変動した際に予測値をリアルタイムで取得する
  const fetchForecastData = async () => {
    try {
      // /simulate に POST するパラメータ
      console.log("現在の入力:", decisionVarRef.current, currentValuesRef.current)

      if (chartPredictMode === 'best-worst') {
        // モード（１）：ベストケース、ワーストケースの２つを計算
        // 上限予測値の計算
        let upperDecisionVar = { ...decisionVarRef.current };
        upperDecisionVar['cp_climate_params'] = 8.5

        const upperBody = {
          user_name: userName,
          scenario_name: scenarioName,
          mode: "Predict Simulation Mode",
          decision_vars: [upperDecisionVar],
          num_simulations: Number(numSimulations),
          current_year_index_seq: currentValuesRef.current
        };

        // axios でリクエスト
        const upresp = await axios.post(`${BACKEND_URL}/simulate`, upperBody);
        if (upresp.data && upresp.data.data) {
          setChartPredictData((prev) => {
            const updated = [...prev];
            updated[1] = upresp.data.data;
            return updated;
          });
        }

        // 下限予測値の計算
        let lowerDecisionVar = { ...decisionVarRef.current };
        lowerDecisionVar['cp_climate_params'] = 1.9

        const lowerBody = {
          user_name: userName,
          scenario_name: scenarioName,
          mode: "Predict Simulation Mode",
          decision_vars: [lowerDecisionVar],
          num_simulations: Number(numSimulations),
          current_year_index_seq: currentValuesRef.current
        };

        // axios でリクエスト
        const resp = await axios.post(`${BACKEND_URL}/simulate`, lowerBody);
        setBlockScores(prev => [...prev, ...resp.data.block_scores]);
        if (resp.data && resp.data.data) {
          setChartPredictData((prev) => {
            const updated = [...prev];
            updated[0] = resp.data.data;
            return updated;
          });
        }
      } else if (chartPredictMode === 'monte-carlo') {
        // モード（２）：１０回のモンテカルロシミュレーション
        const monteCarloResults = [];
        
        for (let i = 0; i < 10; i++) {
          let monteCarloDecisionVar = { ...decisionVarRef.current };
          monteCarloDecisionVar['cp_climate_params'] = decisionVarRef.current.cp_climate_params;

          const monteCarloBody = {
            user_name: userName,
            scenario_name: scenarioName,
            mode: "Predict Simulation Mode",
            decision_vars: [monteCarloDecisionVar],
            num_simulations: Number(numSimulations),
            current_year_index_seq: currentValuesRef.current
          };

          try {
            const resp = await axios.post(`${BACKEND_URL}/simulate`, monteCarloBody);
            if (resp.data && resp.data.data) {
              monteCarloResults.push(resp.data.data);
            }
          } catch (error) {
            console.error(`モンテカルロシミュレーション ${i + 1} 回目でエラー:`, error);
          }
        }

        // モンテカルロ結果をchartPredictDataに設定
        if (monteCarloResults.length > 0) {
          setChartPredictData(monteCarloResults);
        }
      } else if (chartPredictMode === 'none') {
        // モード（３）：予測結果を表示しない
        setChartPredictData([[], []]);
      }
    } catch (error) {
      console.error("API取得エラー:", error);
    }
  };

  // 結果を保存し、リザルト画面へ
  const handleShowResult = async () => {
    try {
      // Record Results Mode で /simulate にPOST
      await axios.post(`${BACKEND_URL}/simulate`, {
        scenario_name: scenarioName,
        user_name: userName,
        mode: "Record Results Mode",
        decision_vars: [decisionVar],
        num_simulations: Number(numSimulations),
        current_year_index_seq: currentValues
      });
    } catch (err) {
      alert("結果保存に失敗しました");
      console.error(err);
    } finally {
      // POSTが終わったら必ずページ遷移
      window.location.href = `${window.location.origin}/results/index.html`;
    }
  };

  // 次のサイクルに移る処理
  const handleNextCycle = () => {
    // --- 「次のサイクル」押下ログを队列に追加 ---
    addLogToQueue({
      type: "EndCycle",
      name: decisionVar.year,
      cycle: currentCycle
    });
    console.log(`🔄 下一个周期按钮点击: 结束周期${currentCycle}`);

    // 新しいサイクルの準備
    setCurrentCycle(prev => prev + 1);
    setCycleCompleted(false);
    setShowResultButton(false);
    setInputCount(0); // 入力カウントをリセット
    setInputHistory([]); // 入力履歴をリセット
    
    // 年を2026年にリセット
    updateDecisionVar("year", 2026);
    
    // シミュレーションデータをクリア（新しいサイクルのため）
    setSimulationData([]);
    
    // 予測データもクリア
    setChartPredictData([[], []]);
    
    // 現在の値を初期状態にリセット（必要に応じて調整）
    setCurrentValues(prev => ({
      ...prev,
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
    }));
  };

  // (B) グラフ描画用データ作成
  // 例として "Temperature (℃)" をシミュレーション1本分だけ描画する
  // 本来は複数Simulation のデータをまとめたりする必要あり
  const filteredSim = simulationData.filter((d) => d.Simulation === 0);
  const chartData = {
    labels: filteredSim.map((d) => d.Year),
    datasets: [
      {
        label: "Temperature (Sim=0)",
        data: filteredSim.map((d) => d["Temperature (℃)"]),
        borderColor: "red",
        fill: false,
      },
    ],
  };

  // (C) シナリオ比較リクエスト例
  const handleCompareScenarios = async () => {
    try {
      const body = {
        scenario_names: [scenarioName, "別のシナリオ名"],
        variables: ["Flood Damage", "Crop Yield", "Ecosystem Level", "Municipal Cost"]
      };
      const resp = await axios.post(`${BACKEND_URL}/compare`, body);
      console.log("Compare result:", resp.data);
      alert("シナリオ比較結果はコンソールに出力しています");
    } catch (err) {
      console.error(err);
      alert("比較に失敗しました");
    }
  };

  // (D) CSV ダウンロード例 (バックエンドの /export/{scenario_name})
  const handleDownloadCSV = async () => {
    try {
      const resp = await axios.get(`${BACKEND_URL}/export/${scenarioName}`, {
        responseType: "blob", // CSVをバイナリとして受け取る
      });

      // ブラウザ上でダウンロードをトリガー
      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${scenarioName}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error(err);
      alert("CSVダウンロードに失敗しました");
    }
  };

  // (E) トレードスペース用UIの表示

  const handleOpenResultUI = () => {
    setOpenResultUI(true);
    // --- 「サイクルの比較」開始をWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "StartCompare",
        timestamp: new Date().toISOString()
      }));
    }
    // ------------------------------------------------------
  };

  const handleCloseResultUI = () => {
    setOpenResultUI(false);
    // --- 「サイクルの比較」終了をWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "EndCompare",
        timestamp: new Date().toISOString()
      }));
    }
    // ------------------------------------------------------
  };
  // X軸変更時
  const handleXAxisChange = (event) => {
    setSelectedXAxis(event.target.value);

    // --- X軸選択変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "ScatterX",
        name: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
  };

  // Y軸変更時
  const handleYAxisChange = (event) => {
    setSelectedYAxis(event.target.value);

    // --- Y軸選択変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "ScatterY",
        name: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
  };

  // プロット属性変更時
  const handlePlotAttributeChange = (event) => {
    setSelectedPlotAttribute(event.target.value);

    // --- 绘图属性选择ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "PlotAttribute",
        name: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
    console.log(`🎨 绘图属性选择: ${event.target.value}`);
  };

  const handleOpenSettings = () => {
    setOpenSettingsDialog(true);
  };

  const handleCloseSettings = () => {
    setOpenSettingsDialog(false);
  };

  // (F) パラメータ周りの変更処理
  const updateDecisionVar = (key, value) => {
    setDecisionVar(prev => {
      // スライダーの場合は表示値をバックエンド値に変換して保存
      const backendValue = convertDisplayToBackendValue(key, value);
      const updated = { ...prev, [key]: backendValue };
      decisionVarRef.current = updated;
      
      // --- スライダー操作ログをWebSocketで送信 ---
      if (key != "year" && wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
        wsLogRef.current.send(JSON.stringify({
          user_name: userName,
          mode: chartPredictMode,
          type: "Slider",
          name: key,
          value: backendValue, // バックエンド値で送信
          timestamp: new Date().toISOString()
        }));
      }
      // --------------------------------------------
      return updated;
    });
  };



  const updateCurrentValues = (newDict) => {
    console.log("更新されるnewDict:", newDict);
    const updated = {
      temp: newDict['Temperature (℃)'],
      precip: newDict['Precipitation (mm)'],
      municipal_demand: newDict['Municipal Demand'],
      available_water: newDict['Available Water'],
      crop_yield: newDict['Crop Yield'],
      hot_days: newDict['Hot Days'],
      extreme_precip_freq: newDict['Extreme Precip Frequency'],
      ecosystem_level: newDict['Ecosystem Level'],
      levee_level: newDict['Levee Level'],                       
      high_temp_tolerance_level: newDict['High Temp Tolerance Level'],
      forest_area: newDict['Forest area'],                      
      resident_capacity: newDict['Resident capacity'],          
      transportation_level: newDict['transportation_level'],    
      levee_investment_total: newDict['Levee investment total'],
      RnD_investment_total: newDict['RnD investment total'],    
      risky_house_total: newDict['risky_house_total'],          
      non_risky_house_total: newDict['non_risky_house_total'],  
      resident_burden: newDict['Resident Burden'],
      biodiversity_level: newDict['biodiversity_level'],

    };
    console.log("更新されるcurrentValues:", updated);
    setCurrentValues(prev => ({ ...prev, ...updated }));
    currentValuesRef.current = { ...currentValuesRef.current, ...updated };
  };

  // chartPredictData[1] のデータを取得
  const xAxisYears = Array.from({ length: 2100 - 2025 + 1 }, (_, i) => 2026 + i);

  const getPredictData = (predicDataArray) => {
    const predictDataMap = new Map();
    if (predicDataArray) {
      predicDataArray.forEach(item => {
        let value = item[selectedIndicator];

        // 選択された指標に対してのみ、変換処理
        const conversionFactor = INDICATOR_CONVERSION[selectedIndicator];
        if (typeof value === 'number' && conversionFactor !== undefined) {
          value = value * conversionFactor;
        }

        predictDataMap.set(item["Year"], value);
      });
    }

    // X軸の各年に対応する温度データの配列を生成（データがない年はnull）
    const formattedPredictData = xAxisYears.map(year => {
      return predictDataMap.has(year) ? predictDataMap.get(year) : null;
    });

    return formattedPredictData
  }

  // バックエンドで受け取ったデータをUI側の単位に合わせる
  const processIndicatorData = (rawData) => {
    return rawData.map(item => {
      const newItem = { ...item };

      // 全ての定義済み指標に対して変換処理
      Object.entries(INDICATOR_CONVERSION).forEach(([key, factor]) => {
        if (typeof newItem[key] === 'number') {
          newItem[key] = newItem[key] * factor;
        }
      });

      return newItem;
    });
  };

  // 選択されたモードに応じてスライダーの操作を制限する関数
  const isSliderEnabled = (sliderName) => {
    switch (selectedMode) {
      case 'group':
        return true; // 全てのスライダーを操作可能
      case 'upstream':
        // 上流モード: 植林・森林保全、河川堤防、田んぼダムのみ操作可能
        return ['planting_trees_amount', 'dam_levee_construction_cost', 'paddy_dam_construction_cost'].includes(sliderName);
      case 'downstream':
        // 下流モード: 田んぼダム、住宅移転、防災訓練・啓発のみ操作可能
        return ['paddy_dam_construction_cost', 'house_migration_amount', 'capacity_building_cost'].includes(sliderName);
      default:
        return true;
    }
  };

  useEffect(() => {
    // chartPredictModeが変更されたときに予測データを再取得
    fetchForecastData();
  }, [chartPredictMode]);

  const t = texts[language]; // 現在の言語のテキストを取得
  const [openFormulaModal, setOpenFormulaModal] = useState(false);

  // RCPの初期値をログ出力
  useEffect(() => {
    console.log('RCP初期値:', decisionVar.cp_climate_params);
  }, []);

  // decisionVarの変更を監視（RCPの値変更確認用）
  useEffect(() => {
    console.log('decisionVar更新:', decisionVar);
  }, [decisionVar]);

  // スライダーの表示値をバックエンド送信値に変換する関数
  const convertDisplayToBackendValue = (key, displayValue) => {
    const conversionMap = {
      'planting_trees_amount': [0, 100, 200],
      'dam_levee_construction_cost': [0, 1, 2], // 既に3段階
      'agricultural_RnD_cost': [0, 5, 10],
      'house_migration_amount': [0, 5, 10],
      'paddy_dam_construction_cost': [0, 5, 10],
      'capacity_building_cost': [0, 5, 10]
    };
    
    const backendValues = conversionMap[key];
    if (backendValues && displayValue >= 0 && displayValue <= 2) {
      return backendValues[displayValue];
    }
    return displayValue; // 変換できない場合はそのまま返す
  };

  // バックエンド送信値を表示値に変換する関数
  const convertBackendToDisplayValue = (key, backendValue) => {
    const conversionMap = {
      'planting_trees_amount': [0, 100, 200],
      'dam_levee_construction_cost': [0, 1, 2],
      'agricultural_RnD_cost': [0, 5, 10],
      'house_migration_amount': [0, 5, 10],
      'paddy_dam_construction_cost': [0, 5, 10],
      'capacity_building_cost': [0, 5, 10]
    };
    
    const backendValues = conversionMap[key];
    if (backendValues) {
      const index = backendValues.indexOf(backendValue);
      return index >= 0 ? index : 0;
    }
    return backendValue; // 変換できない場合はそのまま返す
  };

  return (
    <Box sx={{ padding: 2, backgroundColor: '#f5f7fa', minHeight: '100vh' }}>



      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h4" gutterBottom>
          {t.title}
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography variant="h6" color="primary">
            {t.cycle} {currentCycle}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t.year} {decisionVar.year - 1}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <Typography variant="body2" color="primary" fontWeight="bold">
            {selectedMode === 'group' && t.mode.group}
            {selectedMode === 'upstream' && t.mode.upstream}
            {selectedMode === 'downstream' && t.mode.downstream}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {selectedMode === 'group' && t.mode.groupDesc}
            {selectedMode === 'upstream' && t.mode.upstreamDesc}
            {selectedMode === 'downstream' && t.mode.downstreamDesc}
          </Typography>
        </Box>

        {/* Model Descriptionボタン */}
        <Button variant="outlined" onClick={() => {
          setOpenFormulaModal(true);
          // --- 模型说明打开ログを队列に追加 ---
          addLogToQueue({
            type: "ModelExplanation",
            name: "Open",
            action: "open_model_description"
          });
          console.log(`📖 模型说明页面打开`);
        }}>
          Model Description
        </Button>
        
        {/* RCPの不確実性シナリオ選択スライダー */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
          <Typography variant="body2" sx={{ minWidth: 120 }}>
            {t.rcp.scenario}: {decisionVar.cp_climate_params}
          </Typography>
          <Slider
            value={decisionVar.cp_climate_params}
            onChange={(event, newValue) => {
              console.log('RCPスライダー変更:', newValue);
              updateDecisionVar('cp_climate_params', newValue);
            }}
            step={null}
            marks={[
              { value: 1.9, label: '1.9' },
              { value: 2.6, label: '2.6' },
              { value: 4.5, label: '4.5' },
              { value: 6.0, label: '6.0' },
              { value: 8.5, label: '8.5' }
            ]}
            min={1.9}
            max={8.5}
            sx={{ width: 200 }}
          />
        </Box>
        
        {/* WebSocket状态指示灯 - 左上方 */}
        <Box sx={{ position: 'absolute', top: 16, left: 16, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: logStatus === 'connected' ? '#4caf50' : '#f44336',
              boxShadow: logStatus === 'connected' ? '0 0 8px rgba(76, 175, 80, 0.6)' : '0 0 8px rgba(244, 67, 54, 0.6)',
            }}
          />
          <Typography variant="caption" color="text.secondary">
            WebSocket
          </Typography>
        </Box>

        {/* 右上方按钮组 */}
        <Box sx={{ position: 'absolute', top: 16, right: 16, display: 'flex', gap: 1 }}>
          <Button
            variant="contained"
            color="error"
            size="small"
            onClick={handleEndExperiment}
            sx={{ fontSize: '0.75rem', px: 2 }}
          >
            {language === 'ja' ? '実験終了' : 'End Experiment'}
          </Button>
          <IconButton color="primary" onClick={handleOpenSettings}>
            <SettingsIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Model Description Dialog */}
      <Dialog open={openFormulaModal} onClose={() => setOpenFormulaModal(false)} maxWidth="xl" fullWidth>
        <DialogTitle>Model Description</DialogTitle>
        <DialogContent>
          <ModelExplanationPage />
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Button variant="contained" onClick={() => {
              setOpenFormulaModal(false);
              // --- 模型说明关闭ログを队列に追加 ---
              addLogToQueue({
                type: "ModelExplanation",
                name: "Close",
                action: "close_model_description"
              });
              console.log(`📖 模型说明页面关闭`);
            }}>
              Close
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      <Dialog open={openNameDialog} disableEscapeKeyDown>
        <DialogTitle>{t.dialog.nameTitle}</DialogTitle>
        <DialogContent>
          <TextField
            error={!!userNameError}
            helperText={userNameError}        
            autoFocus
            fullWidth
            value={userName}
            onChange={e => setUserName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && userName.trim()) {
                handleUserNameRegister();
              }
            }}
            label={t.dialog.nameLabel}
            sx={{ mb: 3 }}
          />
          
          <Typography variant="h6" gutterBottom>
            {t.dialog.modeTitle}
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="mode-group"
                name="mode"
                value="group"
                checked={selectedMode === 'group'}
                onChange={(e) => {
                  setSelectedMode(e.target.value);
                  // --- 流域选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "ModeSelect",
                    name: e.target.value,
                    action: "watershed_selection"
                  });
                  console.log(`🏞️ 流域选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="mode-group" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.mode.group}
                </Typography>
              </label>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="mode-upstream"
                name="mode"
                value="upstream"
                checked={selectedMode === 'upstream'}
                onChange={(e) => {
                  setSelectedMode(e.target.value);
                  // --- 流域选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "ModeSelect",
                    name: e.target.value,
                    action: "watershed_selection"
                  });
                  console.log(`🏞️ 流域选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="mode-upstream" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.mode.upstream}
                </Typography>
              </label>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="mode-downstream"
                name="mode"
                value="downstream"
                checked={selectedMode === 'downstream'}
                onChange={(e) => {
                  setSelectedMode(e.target.value);
                  // --- 流域选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "ModeSelect",
                    name: e.target.value,
                    action: "watershed_selection"
                  });
                  console.log(`🏞️ 流域选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="mode-downstream" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.mode.downstream}
                </Typography>
              </label>
            </Box>
          </Box>
          
          <Button
            variant="contained"
            fullWidth
            disabled={!userName.trim()}
            onClick={handleUserNameRegister}
            sx={{ mt: 2 }}
          >
            {t.dialog.register}
          </Button>
        </DialogContent>
      </Dialog>

      {/* 設定ダイアログ */}
      <Dialog open={openSettingsDialog} onClose={handleCloseSettings} maxWidth="sm" fullWidth>
        <DialogTitle>{t.settings.title}</DialogTitle>
        <DialogContent>
          <Typography variant="h6" gutterBottom>
            {t.settings.predictDataMode}
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="predict-best-worst"
                name="chartPredictMode"
                value="best-worst"
                checked={chartPredictMode === 'best-worst'}
                onChange={(e) => {
                  setChartPredictMode(e.target.value);
                  localStorage.setItem('chartPredictMode', e.target.value);
                  // --- 预测模式选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "PredictModeSelect",
                    name: e.target.value,
                    action: "prediction_mode_change"
                  });
                  console.log(`🔮 预测模式选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="predict-best-worst" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.predictMode.bestWorst}
                </Typography>
              </label>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="predict-monte-carlo"
                name="chartPredictMode"
                value="monte-carlo"
                checked={chartPredictMode === 'monte-carlo'}
                onChange={(e) => {
                  setChartPredictMode(e.target.value);
                  localStorage.setItem('chartPredictMode', e.target.value);
                  // --- 预测模式选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "PredictModeSelect",
                    name: e.target.value,
                    action: "prediction_mode_change"
                  });
                  console.log(`🔮 预测模式选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="predict-monte-carlo" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.predictMode.monteCarlo}
                </Typography>
              </label>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="predict-none"
                name="chartPredictMode"
                value="none"
                checked={chartPredictMode === 'none'}
                onChange={(e) => {
                  setChartPredictMode(e.target.value);
                  localStorage.setItem('chartPredictMode', e.target.value);
                  // --- 预测模式选择ログを队列に追加 ---
                  addLogToQueue({
                    type: "PredictModeSelect",
                    name: e.target.value,
                    action: "prediction_mode_change"
                  });
                  console.log(`🔮 预测模式选择: ${e.target.value}`);
                }}
              />
              <label htmlFor="predict-none" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  {t.predictMode.none}
                </Typography>
              </label>
            </Box>
          </Box>
          
          <Typography variant="body1" sx={{ mb: 2 }}>
            {t.settings.predictDataMode}
          </Typography>

          <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
            {t.settings.languageMode}
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="lang-ja"
                name="language"
                value="ja"
                checked={language === 'ja'}
                onChange={(e) => {
                  setLanguage(e.target.value);
                  localStorage.setItem('language', e.target.value);
                  // --- 语言切换ログを队列に追加 ---
                  addLogToQueue({
                    type: "LanguageSelect",
                    name: e.target.value,
                    action: "language_change"
                  });
                  console.log(`🌐 语言切换: ${e.target.value}`);
                }}
              />
              <label htmlFor="lang-ja" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  日本語
                </Typography>
              </label>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <input
                type="radio"
                id="lang-en"
                name="language"
                value="en"
                checked={language === 'en'}
                onChange={(e) => {
                  setLanguage(e.target.value);
                  localStorage.setItem('language', e.target.value);
                  // --- 语言切换ログを队列に追加 ---
                  addLogToQueue({
                    type: "LanguageSelect",
                    name: e.target.value,
                    action: "language_change"
                  });
                  console.log(`🌐 语言切换: ${e.target.value}`);
                }}
              />
              <label htmlFor="lang-en" style={{ marginLeft: 8 }}>
                <Typography variant="body1">
                  English
                </Typography>
              </label>
            </Box>
          </Box>
          <Box sx={{ textAlign: 'center', mt: 0 }}>
            <Button
              variant="contained"
              onClick={handleCloseSettings}
              sx={{ mt: 2 }}
            >
              {t.settings.close}
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {/* 結果表示ダイアログ */}
      <Dialog open={openResultUI} onClose={handleCloseResultUI} maxWidth={false} fullWidth
        PaperProps={{ sx: { width: '90vw', height: '90vh', maxWidth: '1600px' } }}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {t.scatter.title}
          <Button onClick={handleCloseResultUI} color="primary" variant="outlined">
            {language === 'ja' ? '戻る' : 'Back'}
          </Button>
        </DialogTitle>
        <DialogContent>
          {resultHistory.length > 0 ? (
            <Box sx={{ display: 'flex', gap: 4, height: '70vh' }}>
              {/* 左側：散布図セクション */}
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" gutterBottom>
                  {t.scatter.description}
                </Typography>
                
                {/* 軸選択セレクトバー */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                  <FormControl sx={{ minWidth: 200 }}>
                    <InputLabel>{t.scatter.xAxis}</InputLabel>
                    <Select
                      value={selectedXAxis}
                      label={t.scatter.xAxis}
                      onChange={handleXAxisChange}
                    >
                      {Object.keys(getLineChartIndicators(language)).map((key) => (
                        <MenuItem key={key} value={key}>
                          {getLineChartIndicators(language)[key].labelTitle}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  <FormControl sx={{ minWidth: 200 }}>
                    <InputLabel>{t.scatter.yAxis}</InputLabel>
                    <Select
                      value={selectedYAxis}
                      label={t.scatter.yAxis}
                      onChange={handleYAxisChange}
                    >
                      {Object.keys(getLineChartIndicators(language)).map((key) => (
                        <MenuItem key={key} value={key}>
                          {getLineChartIndicators(language)[key].labelTitle}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  
                  <FormControl sx={{ minWidth: 200 }}>
                    <InputLabel>{t.scatter.plotAttribute}</InputLabel>
                    <Select
                      value={selectedPlotAttribute}
                      label={t.scatter.plotAttribute}
                      onChange={handlePlotAttributeChange}
                    >
                      <MenuItem value="average">{t.scatter.average}</MenuItem>
                      <MenuItem value="2050">{t.scatter.year2050}</MenuItem>
                      <MenuItem value="2075">{t.scatter.year2075}</MenuItem>
                      <MenuItem value="2100">{t.scatter.year2100}</MenuItem>
                      <MenuItem value="all">{t.scatter.allDisplay}</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                
                {/* 散布図 */}
                <Box sx={{ flex: 1, minHeight: 400 }}>
                  <ScatterChart
                    width={600}
                    height={400}
                    series={resultHistory.map((cycle, cycleIndex) => {
                      const colors = ['rgba(25, 118, 210, 0.6)', 'rgba(220, 0, 78, 0.6)', 'rgba(56, 142, 60, 0.6)', 'rgba(245, 124, 0, 0.6)', 'rgba(123, 31, 162, 0.6)', 'rgba(211, 47, 47, 0.6)'];
                      const color = colors[cycleIndex % colors.length];
                      
                      // 選択されたプロット属性に応じて対象年を決定
                      let targetYears;
                      if (selectedPlotAttribute === 'all') {
                        targetYears = [2050, 2075, 2100];
                      } else if (selectedPlotAttribute === 'average') {
                        targetYears = ['average'];
                      } else {
                        targetYears = [parseInt(selectedPlotAttribute)];
                      }
                      
                      return targetYears.map((year) => {
                        let yearData;
                        
                        if (year === 'average') {
                          // 2026年～2100年の全データの平均値を計算
                          const validData = cycle.simulationData.filter(data =>
                            typeof data[selectedXAxis] === 'number' && typeof data[selectedYAxis] === 'number'
                          );
                          if (validData.length === 0) return null;
                          const avgX = validData.reduce((sum, d) => sum + d[selectedXAxis], 0) / validData.length;
                          const avgY = validData.reduce((sum, d) => sum + d[selectedYAxis], 0) / validData.length;
                          yearData = {
                            [selectedXAxis]: avgX,
                            [selectedYAxis]: avgY
                          };
                        } else {
                          yearData = cycle.simulationData.find(data => data.Year === year);
                        }
                        
                        if (!yearData) {
                          console.log(`サイクル${cycle.cycleNumber}の${year}年のデータが見つかりません`);
                          return null;
                        }
                        
                        // 年ごとに異なるマーカーサイズと透明度を設定
                        let markerSize, opacity;
                        if (year === 'average') {
                          markerSize = 10;
                          opacity = 0.7;
                        } else {
                          switch (year) {
                            case 2050:
                              markerSize = 6;
                              opacity = 0.8;
                              break;
                            case 2075:
                              markerSize = 8;
                              opacity = 0.6;
                              break;
                            case 2100:
                              markerSize = 10;
                              opacity = 0.4;
                              break;
                            default:
                              markerSize = 6;
                              opacity = 0.8;
                          }
                        }
                        
                        return {
                          data: [{
                            x: yearData[selectedXAxis] || 0,
                            y: yearData[selectedYAxis] || 0,
                          }],
                          color: color.replace('0.6', opacity.toString()),
                          markerSize: markerSize,
                          showMark: true,
                        };
                      }).filter(Boolean);
                    }).flat()}
                    xAxis={[{
                      label: getLineChartIndicators(language)[selectedXAxis]?.labelTitle || '',
                      min: 0,
                      max: Math.max(...resultHistory.flatMap(cycle => 
                        cycle.simulationData.map(data => data[selectedXAxis] || 0)
                      )) * 1.1
                    }]}
                    yAxis={[{
                      label: getLineChartIndicators(language)[selectedYAxis]?.labelTitle || '',
                      min: 0,
                      max: Math.max(...resultHistory.flatMap(cycle => 
                        cycle.simulationData.map(data => data[selectedYAxis] || 0)
                      )) * 1.1
                    }]}
                    legend={null}
                  />
                </Box>
                
                {/* 凡例の説明 */}
                <Box sx={{ mt: 2, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      {t.scatter.markerSize}
                    </Typography>
                    {selectedPlotAttribute === 'all' && (
                      <>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <Box sx={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#666', opacity: 0.8, display: 'inline-block' }}></Box>
                          <Typography variant="caption">{t.scatter.small}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#666', opacity: 0.6, display: 'inline-block' }}></Box>
                          <Typography variant="caption">{t.scatter.medium}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#666', opacity: 0.4, display: 'inline-block' }}></Box>
                          <Typography variant="caption">{t.scatter.large}</Typography>
                        </Box>
                      </>
                    )}
                    {selectedPlotAttribute === 'average' && (
                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#666', opacity: 0.5, display: 'inline-block' }}></Box>
                        <Typography variant="caption">{t.scatter.average}</Typography>
                      </Box>
                    )}
                    {['2050', '2075', '2100'].includes(selectedPlotAttribute) && (
                      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <Box sx={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#666', opacity: 0.7, display: 'inline-block' }}></Box>
                        <Typography variant="caption">{t.scatter[`year${selectedPlotAttribute}`]}</Typography>
                      </Box>
                    )}
                  </Box>
                  
                  <Box>
                    <Typography variant="body2" fontWeight="bold" gutterBottom>
                      {t.scatter.cycleColor}
                    </Typography>
                    {resultHistory.map((cycle, index) => {
                      const colors = ['#1976d2', '#dc004e', '#388e3c', '#f57c00', '#7b1fa2', '#d32f2f', '#00796b', '#c2185b', '#ffa000', '#0097a7'];
                      const color = colors[index % colors.length];
                      
                      return (
                        <Box key={index} sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <Box sx={{ width: 12, height: 12, backgroundColor: color, display: 'inline-block' }}></Box>
                          <Typography variant="caption">{t.scatter.cycle} {cycle.cycleNumber}</Typography>
                        </Box>
                      );
                    })}
                  </Box>
                </Box>
              </Box>
              
              {/* 右側：入力履歴テーブル */}
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" gutterBottom>
                  {t.scatter.inputHistory}
                </Typography>
                
                {/* 年次・サイクル・ソートセレクトバー */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                  <FormControl sx={{ minWidth: 120 }}>
                    <InputLabel>{t.scatter.yearFilter}</InputLabel>
                    <Select
                      value={selectedYearFilter}
                      label={t.scatter.yearFilter}
                      onChange={(event) => {
                        setSelectedYearFilter(event.target.value);
                        // --- 年份过滤ログをWebSocketで送信 ---
                        if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
                          wsLogRef.current.send(JSON.stringify({
                            user_name: userName,
                            mode: chartPredictMode,
                            type: "YearFilter",
                            name: event.target.value,
                            cycle: currentCycle,
                            timestamp: new Date().toISOString()
                          }));
                        }
                        console.log(`📅 年份过滤选择: ${event.target.value}`);
                      }}
                    >
                      <MenuItem value="all">{t.scatter.allYears}</MenuItem>
                      {/* 年次リストを動的に生成 */}
                      {Array.from(new Set(resultHistory.flatMap(cycle => cycle.inputHistory.map(input => input.year)))).sort((a, b) => a - b).map(year => (
                        <MenuItem key={year} value={year}>{year}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControl sx={{ minWidth: 120 }}>
                    <InputLabel>{t.scatter.cycleFilter}</InputLabel>
                    <Select
                      value={selectedCycleFilter}
                      label={t.scatter.cycleFilter}
                      onChange={(event) => {
                        setSelectedCycleFilter(event.target.value);
                        // --- 周期过滤ログをWebSocketで送信 ---
                        if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
                          wsLogRef.current.send(JSON.stringify({
                            user_name: userName,
                            mode: chartPredictMode,
                            type: "CycleFilter",
                            name: event.target.value,
                            cycle: currentCycle,
                            timestamp: new Date().toISOString()
                          }));
                        }
                        console.log(`🔄 周期过滤选择: ${event.target.value}`);
                      }}
                    >
                      <MenuItem value="all">{t.scatter.allCycles}</MenuItem>
                      {/* サイクル番号リストを動的に生成 */}
                      {resultHistory.map(cycle => (
                        <MenuItem key={cycle.cycleNumber} value={cycle.cycleNumber}>{t.scatter.cycle} {cycle.cycleNumber}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControl sx={{ minWidth: 120 }}>
                    <InputLabel>{t.scatter.historySort}</InputLabel>
                    <Select
                      value={selectedHistorySort}
                      label={t.scatter.historySort}
                      onChange={(event) => {
                        setSelectedHistorySort(event.target.value);
                        // --- 历史排序ログをWebSocketで送信 ---
                        if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
                          wsLogRef.current.send(JSON.stringify({
                            user_name: userName,
                            mode: chartPredictMode,
                            type: "HistorySort",
                            name: event.target.value,
                            cycle: currentCycle,
                            timestamp: new Date().toISOString()
                          }));
                        }
                        console.log(`📊 历史排序选择: ${event.target.value}`);
                      }}
                    >
                      <MenuItem value="cycle">{t.scatter.sortByCycle}</MenuItem>
                      <MenuItem value="year">{t.scatter.sortByYear}</MenuItem>
                      <MenuItem value="input">{t.scatter.sortByInput}</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
                
                <Box sx={{ flex: 1, overflow: 'auto' }}>
                  <TableContainer component={Paper} sx={{ maxHeight: '100%' }}>
                    <Table size="small" aria-label={t.scatter.inputHistory} stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell>{t.scatter.cycle}</TableCell>
                          <TableCell>{t.scatter.inputCount}</TableCell>
                          <TableCell>{t.scatter.inputYear}</TableCell>
                          <TableCell>{t.rcp.scenario}</TableCell>
                          <TableCell>{t.sliders.plantingTrees}</TableCell>
                          <TableCell>{t.sliders.houseMigration}</TableCell>
                          <TableCell>{t.sliders.damLevee}</TableCell>
                          <TableCell>{t.sliders.paddyDam}</TableCell>
                          <TableCell>{t.sliders.capacityBuilding}</TableCell>
                          {/* <TableCell>{t.sliders.transportation}</TableCell> */}
                          <TableCell>{t.sliders.agriculturalRnD}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {resultHistory.flatMap((cycle, cycleIndex) =>
                          cycle.inputHistory
                            .filter(input =>
                              (selectedYearFilter === 'all' || input.year === Number(selectedYearFilter)) &&
                              (selectedCycleFilter === 'all' || cycle.cycleNumber === Number(selectedCycleFilter))
                            )
                            .sort((a, b) => {
                              if (selectedHistorySort === 'cycle') {
                                return cycle.cycleNumber - cycle.cycleNumber;
                              } else if (selectedHistorySort === 'year') {
                                return a.year - b.year;
                              } else if (selectedHistorySort === 'input') {
                                return a.inputNumber - b.inputNumber;
                              }
                              return 0;
                            })
                            .map((input, inputIndex) => (
                              <TableRow key={`${cycleIndex}-${inputIndex}`}>
                                <TableCell>{cycle.cycleNumber}</TableCell>
                                <TableCell>{input.inputNumber}回目</TableCell>
                                <TableCell>{input.year}年</TableCell>
                                <TableCell>{input.decisionVariables.cp_climate_params}</TableCell>
                                <TableCell>{convertBackendToDisplayValue('planting_trees_amount', input.decisionVariables.planting_trees_amount)}</TableCell>
                                <TableCell>{convertBackendToDisplayValue('house_migration_amount', input.decisionVariables.house_migration_amount)}</TableCell>
                                <TableCell>{convertBackendToDisplayValue('dam_levee_construction_cost', input.decisionVariables.dam_levee_construction_cost)}</TableCell>
                                <TableCell>{convertBackendToDisplayValue('paddy_dam_construction_cost', input.decisionVariables.paddy_dam_construction_cost)}</TableCell>
                                <TableCell>{convertBackendToDisplayValue('capacity_building_cost', input.decisionVariables.capacity_building_cost)}</TableCell>
                                {/* <TableCell>{input.decisionVariables.transportation_invest}</TableCell> */}
                                <TableCell>{convertBackendToDisplayValue('agricultural_RnD_cost', input.decisionVariables.agricultural_RnD_cost)}</TableCell>
                              </TableRow>
                            ))
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              </Box>
            </Box>
          ) : (
            <Typography variant="body1" color="text.secondary">
              {t.scatter.noCompletedCycles}
            </Typography>
          )}
        </DialogContent>
      </Dialog>

      {/* メインレイアウト */}
      <Box sx={{ display: 'flex', width: '100%', marginBottom: 1, gap: 3 }}>
        {/* 左側：画像 */}
        <Paper
          elevation={3}
          sx={{
            position: 'relative',
            width: '60%',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >

          <Box sx={{ position: 'relative', width: '100%' }}>
            <img
              src="/stockflow_mayfes.png"
              alt="サンプル画像"
              style={{ width: '100%', display: 'block', height: 'auto' }}
            />
          </Box>

        </Paper>

        {/* 右側：ゲージ＋グラフ */}
        <Paper
          elevation={3}
          sx={{
            width: '40%',
            padding: 3,
            borderRadius: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            backgroundColor: '#ffffff',
          }}
        >
          {/* ゲージセクション */}
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              {t.year} {decisionVar.year - 1} {t.chart.weatherCondition}
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 2 }}>
              {/* 各ゲージ */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>{t.chart.averageTemp}</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.temp * 100) / 100} valueMax={40} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>{t.unit.celsius}</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>{t.chart.annualPrecip}</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.precip * 10) / 10} valueMax={2000} valueMin={500} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>{t.unit.mm}</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>{t.chart.heavyRainFreq}</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.extreme_precip_freq)} valueMax={10} valueMin={0} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>{t.unit.frequency}</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>{t.chart.residentBurden}</Typography>
                <Gauge width={100} height={100} value={currentValues.resident_burden * INDICATOR_CONVERSION["Municipal Cost"]} valueMax={10} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>{t.unit.manYen}</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>{t.chart.biodiversity}</Typography>
                <Gauge width={100} height={100} value={currentValues.ecosystem_level} valueMax={100} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>{t.unit.none}</Typography>
              </Box>
            </Box>
          </Box>


          {/* グラフ */}
          <LineChart
            xAxis={[
              {
                data: xAxisYears,
                label: t.chart.years,
                scaleType: 'linear',
                tickMinStep: 1,
                showGrid: true,
                min: 2020,
                max: 2100
              },
            ]}
            yAxis={[
              {
                label: `${getLineChartIndicators(language)[selectedIndicator].labelTitle}（${getLineChartIndicators(language)[selectedIndicator].unit}）`,
                min: getLineChartIndicators(language)[selectedIndicator].min,
                max: getLineChartIndicators(language)[selectedIndicator].max,
                showGrid: true
              },
            ]}
            series={[
              {
                data: simulationData.map((row) => row[selectedIndicator]),
                label: t.chart.measuredValue,
                color: '#ff5722',
                showMark: false,
              },
              // 予測データの表示（モードに応じて変更）
              ...(chartPredictMode === 'best-worst' ? [
                {
                  data: getPredictData(chartPredictData[1]),
                  label: t.chart.upperLimit,
                  color: '#cccccc',
                  lineStyle: 'dashed',
                  showMark: false
                },
                {
                  data: getPredictData(chartPredictData[0]),
                  label: t.chart.lowerLimit,
                  color: '#cccccc',
                  lineStyle: 'dashed',
                  showMark: false
                }
              ] : chartPredictMode === 'monte-carlo' ? 
                chartPredictData.map((data, index) => ({
                  data: getPredictData(data),
                  label: `${t.chart.monteCarlo} ${index + 1}`,
                  color: `rgba(100, 100, 100, 0.1)`,
                  lineStyle: 'dashed',
                  lineWidth: 1,
                  showMark: false
                })) : []
              )
            ]}
            height={300}
            sx={{
              width: '100%',
              '& .MuiChartsLegend-root': { display: 'none' },
              backgroundColor: '#f9f9f9',
              borderRadius: 2,
              padding: 2,
            }}
          />

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel id="indicator-select-label">{t.chart.selectYAxis}</InputLabel>
            <Select
              labelId="indicator-select-label"
              value={selectedIndicator}
              label={t.chart.selectYAxis}
              onChange={handleLineChartChange}
            >
              {Object.keys(getLineChartIndicators(language)).map((key) => (
                <MenuItem key={key} value={key}>
                  {getLineChartIndicators(language)[key].labelTitle}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* サイクル情報と次のサイクルボタン */}
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 0 }}>
                {t.cycle} {currentCycle}
              </Typography>
              
              {/* 25年進めるボタンまたは次のサイクルボタン */}
              {!cycleCompleted ? (
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleClickCalc}
                  disabled={inputCount >= 3}
                  size="large"
                  startIcon={<PlayCircle />}
                >
                  {inputCount >= 3 ? t.buttons.inputComplete : t.buttons.advanceYears}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleNextCycle}
                  size="large"
                >
                  {t.buttons.nextCycle} {currentCycle + 1} {t.buttons.startNext}
                </Button>
              )}

              {/* 散布図ポップアップ表示ボタン */}
              <Button
                variant="contained"
                color="primary"
                size="large"
                // sx={{ fontWeight: 'bold', ml: 2, boxShadow: 3 }}
                onClick={handleOpenResultUI}
                startIcon={<InfoIcon />}
              >
                {t.scatter.title}
              </Button>
            </Box>
            
            {cycleCompleted && (
              <Typography variant="body2" color="success.main" gutterBottom>
                {t.buttons.cycleComplete} {currentCycle} {t.buttons.completed}
              </Typography>
            )}
          </Box>
        </Paper>
      </Box>
      <Box style={{ width: '100%' }}>
        <Grid container spacing={2}> {/* spacingでBox間の余白を調整できます */}
          <Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Forest color="success" />
              {t.sliders.plantingTrees}
              <Slider
                value={convertBackendToDisplayValue('planting_trees_amount', decisionVar.planting_trees_amount)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('planting_trees_amount', newValue)}
                disabled={!isSliderEnabled('planting_trees_amount')}
              />
            </Box>
          </Grid>
          {/* <Grid size={3}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <EmojiTransportation color="action"  />
              {t.sliders.transportation}
              <Slider
                value={decisionVar.transportation_invest}
                min={0}
                max={10}
                marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('transportation_invest', newValue)}
                disabled={!isSliderEnabled('transportation_invest')}
              />
            </Box>
          </Grid> */}
          <Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Flood color="info"  />
              {t.sliders.damLevee}
              <Slider
                value={convertBackendToDisplayValue('dam_levee_construction_cost', decisionVar.dam_levee_construction_cost)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('dam_levee_construction_cost', newValue)}
                disabled={!isSliderEnabled('dam_levee_construction_cost')}
              />
            </Box>
          </Grid><Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Biotech color="success"  />
              {t.sliders.agriculturalRnD}
              <Slider
                value={convertBackendToDisplayValue('agricultural_RnD_cost', decisionVar.agricultural_RnD_cost)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('agricultural_RnD_cost', newValue)}
                disabled={!isSliderEnabled('agricultural_RnD_cost')}
              />
            </Box>
          </Grid><Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Houseboat color={"info"} />
              {t.sliders.houseMigration}
              <Slider
                value={convertBackendToDisplayValue('house_migration_amount', decisionVar.house_migration_amount)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('house_migration_amount', newValue)}
                disabled={!isSliderEnabled('house_migration_amount')}
              />
            </Box>
          </Grid><Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Agriculture color={"success"} />
              {t.sliders.paddyDam}
              <Slider
                value={convertBackendToDisplayValue('paddy_dam_construction_cost', decisionVar.paddy_dam_construction_cost)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('paddy_dam_construction_cost', newValue)}
                disabled={!isSliderEnabled('paddy_dam_construction_cost')}
              />
            </Box>
          </Grid><Grid size={4}>
            <Box
              sx={{
                width: '100%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '6px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <LocalLibrary color="action" />
              {t.sliders.capacityBuilding}
              <Slider
                value={convertBackendToDisplayValue('capacity_building_cost', decisionVar.capacity_building_cost)}
                min={0}
                max={2}
                marks={[
                  { value: 0, label: '0' },
                  { value: 1, label: '1' },
                  { value: 2, label: '2' }
                ]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('capacity_building_cost', newValue)}
                disabled={!isSliderEnabled('capacity_building_cost')}
              />
            </Box>
          </Grid>
        </Grid>
      </Box>

    </Box >
  );
}

export default AppRouter;