import React, { useState, useRef, useEffect, useMemo } from "react";
import { Box, Button, Dialog, DialogTitle, DialogContent, FormControl, Grid, IconButton, InputLabel, MenuItem, Slider, Stack, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Paper, TextField } from '@mui/material';
import { LineChart, ScatterChart, Gauge } from '@mui/x-charts';
import { Agriculture, Biotech, EmojiTransportation, Flood, Forest, Houseboat, LocalLibrary, PlayCircle } from '@mui/icons-material';
import InfoIcon from '@mui/icons-material/Info';
import SettingsIcon from '@mui/icons-material/Settings';
import axios from "axios";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import ExpertApp from './ExpertApp';
import FormulaPage from "./FormulaPage"; // 新ページ
import { texts } from "./texts"; // テキスト定義をインポート

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
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";

// 各種設定

const getLineChartIndicators = (language) => {
  const indicators = {
    ja: {
      'Flood Damage': { labelTitle: '洪水被害', max: 1000000, min: 0, unit: 'ドル' },
      'Crop Yield': { labelTitle: '収穫量', max: 6000, min: 0, unit: 'kg/ha' },
      'Ecosystem Level': { labelTitle: '生態系', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: '予算', max: 10000000, min: 0, unit: 'ドル' },
      'Temperature (℃)': { labelTitle: '【気候要素】年平均気温', max: 20, min: 12, unit: '℃' },
      'Precipitation (mm)': { labelTitle: '【気候要素】年降水量', max: 3000, min: 0, unit: 'mm' },
      'Extreme Precip Frequency': { labelTitle: '【気候要素】極端降水頻度', max: 3, min: 0, unit: 'times/year' },
      'Levee Level': { labelTitle: '【中間要素】堤防レベル', max: 400, min: 0, unit: 'mm' },
      'Forest Area': { labelTitle: '【中間要素】森林面積', max: 7000, min: 0, unit: 'ha' },
      'risky_house_total': { labelTitle: '【中間要素】高リスク地域住民', max: 20000, min: 0, unit: 'person' },
      'Resident capacity': { labelTitle: '【中間要素】住民防災能力レベル', max: 1, min: 0, unit: '-' },
      'paddy_dam_area': { labelTitle: '【中間要素】田んぼダムの面積', max: 500, min: 0, unit: 'ha' },
      'available_water': { labelTitle: '【中間要素】利用可能な水量', max: 3000, min: 0, unit: 'mm' },
    },
    en: {
      'Flood Damage': { labelTitle: 'Flood Damage', max: 1000000, min: 0, unit: 'USD' },
      'Crop Yield': { labelTitle: 'Crop Yield', max: 6000, min: 0, unit: 'kg/ha' },
      'Ecosystem Level': { labelTitle: 'Ecosystem Level', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: 'Municipal Cost', max: 10000000, min: 0, unit: 'USD' },
      'Temperature (℃)': { labelTitle: '[Climate] Average Temperature', max: 20, min: 12, unit: '°C' },
      'Precipitation (mm)': { labelTitle: '[Climate] Annual Precipitation', max: 3000, min: 0, unit: 'mm' },
      'Extreme Precip Frequency': { labelTitle: '[Climate] Extreme Precip Frequency', max: 3, min: 0, unit: 'times/year' },
      'Levee Level': { labelTitle: '[Intermediate] Levee Level', max: 400, min: 0, unit: 'mm' },
      'Forest Area': { labelTitle: '[Intermediate] Forest Area', max: 7000, min: 0, unit: 'ha' },
      'risky_house_total': { labelTitle: '[Intermediate] High Risk Area Residents', max: 20000, min: 0, unit: 'person' },
      'Resident capacity': { labelTitle: '[Intermediate] Residents\' Capacity', max: 1, min: 0, unit: '-' },
      'paddy_dam_area': { labelTitle: '[Intermediate] Paddy Dam Area', max: 500, min: 0, unit: 'ha' },
      'available_water': { labelTitle: '[Intermediate] Available Water', max: 3000, min: 0, unit: 'mm' },
    }
  };
  return indicators[language] || indicators.ja;
};

const SIMULATION_YEARS = 25 // 一回のシミュレーションで進める年数を決定する 
const LINE_CHART_DISPLAY_INTERVAL = 100 // ms
const INDICATOR_CONVERSION = {
  // 'Municipal Cost': 1 / 100, // USD → 万円
  // 'Flood Damage': 1 / 100, // USD → 万円
  // 'Crop Yield': 1 / 1000 // kg → ton（例）
};



function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/formula" element={<FormulaPage />} />
        <Route path="/analyze" element={<ExpertApp />} />
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
  const [selectedYearFilter, setSelectedYearFilter] = useState('all'); // 年次フィルター選択
  const [selectedCycleFilter, setSelectedCycleFilter] = useState('all'); // サイクルフィルター選択
  const [chartPredictMode, setChartPredictMode] = useState(localStorage.getItem('chartPredictMode') || 'monte-carlo'); // 予測データ表示モード: 'best-worst', 'monte-carlo', 'none'
  const [language, setLanguage] = useState(localStorage.getItem('language') || 'en'); // 言語モード: 'ja', 'en'
  const [visibleCycles, setVisibleCycles] = useState(new Set()); // 表示するサイクルのセット
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
    temp: 15.5,
    precip: 1700,
    municipal_demand: 100,
    available_water: 1000,
    crop_yield: 100,
    hot_days: 30,
    extreme_precip_freq: 0.1,
    ecosystem_level: 100,
    levee_level: 100,
    high_temp_tolerance_level: 0,
    forest_area: 5000,
    planting_history: {},
    urban_level: 100,
    resident_capacity: 0,
    transportation_level: 0,
    levee_investment_total: 0,
    RnD_investment_total: 0,
    risky_house_total: 15000,
    non_risky_house_total: 0,
    resident_burden: 0,
    biodiversity_level: 100,
    paddy_dam_area:0
  })
  const [simulationData, setSimulationData] = useState([]); // 結果格納


  const [flashOn, setFlashOn] = useState(false);
  const lastFlashAtRef = useRef(0); // 連続点滅の抑制用
  const FLOOD_THRESHOLD = 100;      // 閾値（必要なら設定ダイアログに出してOK）
  const FLASH_COOLDOWN_MS = 500;   // 1.5秒以内の連続発火を抑制
  const FLASH_DURATION_MS = 500;    // 点滅の長さ

  const triggerFlash = () => {
    const now = Date.now();
    if (now - lastFlashAtRef.current < FLASH_COOLDOWN_MS) return; // 連続発火防止
    lastFlashAtRef.current = now;

    setFlashOn(true);
    setTimeout(() => setFlashOn(false), FLASH_DURATION_MS);
  };

  
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

    // --- 縦軸選択変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "GraphSelect",
        name: event.target.value,
        timestamp: new Date().toISOString()
      }));
    }
  };

  const [userName, setUserName] = useState(localStorage.getItem('userName') || '');
  const [openNameDialog, setOpenNameDialog] = useState(!userName);
  const [blockScores, setBlockScores] = useState([]);   // Array<Backend BlockRaw>
  const [ranking,setRanking] = useState([]);
  const [showResultButton, setShowResultButton] = useState(false);
  const [userNameError, setUserNameError] = useState("")
  const [selectedMode, setSelectedMode] = useState(localStorage.getItem('selectedMode') || 'group'); // モード選択: 'group', 'upstream', 'downstream'

    // /ranking の全体データ（既に fetchRanking があるのでそれを活用）
  const [globalRankingRows, setGlobalRankingRows] = useState([]);

  // サイクル別の「平均値」と「順位」
  const [cycleAverages, setCycleAverages] = useState({}); // { cycleNumber: { key: avg, ... } }
  const [cycleRanks, setCycleRanks] = useState({});       // { cycleNumber: { key: {rank,total} } }

  // ここでuseRefを定義
  const wsLogRef = useRef(null);

  const [showYearlyDots, setShowYearlyDots] = useState(true);

  // 散布図セクションの上あたりに追加（関数なのでどこでもOK）
  const baseRGB = [
    [25,118,210], [220,0,78], [56,142,60], [245,124,0],
    [123,31,162], [211,47,47], [0,121,107], [194,24,91],
    [255,160,0], [0,151,167],
  ];
  const makeColor = (idx, a=0.6) => {
    const [r,g,b] = baseRGB[idx % baseRGB.length];
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  };

  const RANK_METRICS = [
    { key: 'Flood Damage',     ja: '洪水被害',  lowerIsBetter: true  },
    { key: 'Ecosystem Level',  ja: '生態系',    lowerIsBetter: false },
    { key: 'Crop Yield',       ja: '収穫量',    lowerIsBetter: false },
    { key: 'Municipal Cost',   ja: '予算',      lowerIsBetter: true  },
  ];

  // 1サイクルの期間平均（2026-2100の全レコード平均）
  const getCycleAverages = (cycle) => {
    const rows = cycle?.simulationData ?? [];
    const sums = {}; const counts = {};
    RANK_METRICS.forEach(m => { sums[m.key] = 0; counts[m.key] = 0; });
    rows.forEach(r => {
      RANK_METRICS.forEach(m => {
        const v = r[m.key];
        if (typeof v === 'number' && !Number.isNaN(v)) { sums[m.key] += v; counts[m.key]++; }
      });
    });
    const avg = {};
    RANK_METRICS.forEach(m => { avg[m.key] = counts[m.key] ? (sums[m.key] / counts[m.key]) : null; });
    return avg;
  };

  // 自分のサイクル（resultHistory）同士でランク付け
  const { latestCycleNumber, latestRanks, totalCycles } = useMemo(() => {
    if (!resultHistory || resultHistory.length === 0) {
      return { latestCycleNumber: null, latestRanks: null, totalCycles: 0 };
    }

    const totalCycles = resultHistory.length;
    const items = resultHistory.map(cycle => ({
      id: cycle.cycleNumber,
      values: getCycleAverages(cycle),
    }));

    // 指標ごとに並べ替え→順位を付与
    const rankTable = {}; // { cycleNumber: { key: rank } }
    items.forEach(it => { rankTable[it.id] = {}; });

    RANK_METRICS.forEach(m => {
      const valid = items
        .filter(it => typeof it.values[m.key] === 'number')
        .sort((a, b) =>
          m.lowerIsBetter
            ? (a.values[m.key] - b.values[m.key])
            : (b.values[m.key] - a.values[m.key])
        );
      valid.forEach((it, i) => {
        rankTable[it.id][m.key] = i + 1; // 1位始まり
      });
      // 値なしは最下位扱い
      items
        .filter(it => typeof it.values[m.key] !== 'number')
        .forEach(it => { rankTable[it.id][m.key] = totalCycles; });
    });

    const latestCycleNumber = resultHistory[resultHistory.length - 1].cycleNumber;
    const latestRanks = rankTable[latestCycleNumber];

    return { latestCycleNumber, latestRanks, totalCycles };
  }, [resultHistory]);

  // 与えられた「候補集合（全参加者 or 自分のサイクル）」に対する順位を返す
  // items: [{ id, values: { 'Flood Damage': 123, ... } }, ...]
  const calcRanks = (items, lowerIsBetterMap) => {
    const ranks = {}; // { id: {key: rank, total: N} }
    const N = items.length || 0;
    items.forEach(it => { ranks[it.id] = {}; });

    RANK_METRICS.forEach(m => {
      // 値がnullのものは末尾に回すためにフィルタ
      const valid = items.filter(it => typeof it.values[m.key] === 'number');
      const invalid = items.filter(it => typeof it.values[m.key] !== 'number');

      // 小さいほど良い or 大きいほど良いで並べ替え
      valid.sort((a, b) => {
        const av = a.values[m.key], bv = b.values[m.key];
        return lowerIsBetterMap[m.key] ? av - bv : bv - av;
      });

      // 順位付け（同値は同順位にしても良いが、ここでは単純に配列順で 1,2,3…）
      valid.forEach((it, i) => {
        ranks[it.id][m.key] = { rank: i + 1, total: N };
      });
      // 値なしは最下位扱い
      invalid.forEach(it => {
        ranks[it.id][m.key] = { rank: N, total: N };
      });
    });

    return ranks;
  };

  // ここでuseEffectを定義
  useEffect(() => {
    wsLogRef.current = new WebSocket("ws://localhost:8000/ws/log");
    wsLogRef.current.onopen = () => {
      console.log("✅ Log WebSocket connected");
    };
    wsLogRef.current.onerror = (e) => {
      console.error("Log WebSocket error", e);
    };
    return () => {
      wsLogRef.current && wsLogRef.current.close();
    };
  }, []);

  const fetchRanking = async () => {
    const res = await axios.get(`${BACKEND_URL}/ranking`);
    setRanking(res.data);
  };

  // ↓ fetchRanking を少し拡張（setGlobalRankingRowsも設定）
  const fetchRankingExtended = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/ranking`);
      setRanking(res.data);           // 既存の用途があれば継続
      setGlobalRankingRows(res.data); // 全参加者分を保持
    } catch (e) {
      console.error('ranking取得失敗', e);
      setGlobalRankingRows([]);       // フェイルセーフ
    }
  };

  const handleUserNameRegister = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/block_scores`); // ここはAPIでCSV読ませる形にする
      const existingUsers = new Set(res.data.map(row => row.user_name));
      
      if (existingUsers.has(userName.trim())) {
        setUserNameError(t.dialog.nameError);
      } else {
        localStorage.setItem('userName', userName.trim());
        localStorage.setItem('selectedMode', selectedMode); // 選択されたモードも保存
        localStorage.setItem('chartPredictMode', chartPredictMode); // 予測モードも保存
        setUserName(userName.trim());
        setOpenNameDialog(false);
        setUserNameError(""); // エラー解除

        // --- ユーザ名をWebSocketで送信 ---
        if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
          wsLogRef.current.send(JSON.stringify({
            user_name: userName,
            mode: chartPredictMode,
            type: "Register",
            timestamp: new Date().toISOString()
          }));
        }
        // ------------------------------------------------------
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
    // 開発中のみ userName を強制リセット
    if (process.env.NODE_ENV === 'development') {
      localStorage.removeItem('userName');
      localStorage.removeItem('selectedMode'); // モードもリセット
      localStorage.removeItem('chartPredictMode'); // 予測モードもリセット
    }
  
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
    const ws = new WebSocket("ws://localhost:3001");

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
                planting_trees_amount: 50,
                house_migration_amount: 50,
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
        setSimulationData(prev => {
          const next = [...prev, ...processedData];

          // ★ ここで直近追加分をチェック
          // 追加分の中に「洪水被害 > 閾値」があれば点滅
          const newlyAdded = processedData;
          const floodHit = newlyAdded.some(row =>
            typeof row['Flood Damage'] === 'number' && row['Flood Damage'] > FLOOD_THRESHOLD
          );
          if (floodHit) triggerFlash();

          return next;
        });

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
    // --- 「25年進める」押下ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "Next",
        name: decisionVar.year,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
    // ------------------------------------------------------

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
      
      // --- 25年進めた後の最終値をWebSocketで送信 ---
      if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
        wsLogRef.current.send(JSON.stringify({
          user_name: userName,
          mode: chartPredictMode,
          type: "Result",
          cycle: currentCycle,
          finalValues: { ...currentValues },
          // (i)全データを抽出する場合
          // simulationData: latestSimulationData,
          // (ii)25, 50, 75年目のみ抽出する場合
          simulationData: [latestSimulationData[24], latestSimulationData[49], latestSimulationData[74]],
          timestamp: new Date().toISOString()
        }));
      }
      // ------------------------------------------------------
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
        // モード（２）：3回のモンテカルロシミュレーション
        const monteCarloResults = [];
        
        for (let i = 0; i < 3; i++) {
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
    // --- 「次のサイクル」押下ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "EndCycle",
        name: decisionVar.year,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
    // ------------------------------------------------------

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
      temp: 15.5,
      precip: 1700,
      municipal_demand: 100,
      available_water: 1000,
      crop_yield: 100,
      hot_days: 30,
      extreme_precip_freq: 0.1,
      ecosystem_level: 100,
      levee_level: 100,
      high_temp_tolerance_level: 0,
      forest_area: 5000,
      planting_history: {},
      urban_level: 100,
      resident_capacity: 0,
      transportation_level: 0,
      levee_investment_total: 0,
      RnD_investment_total: 0,
      risky_house_total: 15000,
      non_risky_house_total: 0,
      resident_burden: 0,
      biodiversity_level: 100,
      paddy_dam_area:0
    }));
  };

  // サイクル表示/非表示の切り替え
  const handleCycleVisibilityChange = (cycleNumber, isVisible) => {
    setVisibleCycles(prev => {
      const newSet = new Set(prev);
      if (isVisible) {
        newSet.add(cycleNumber);
      } else {
        newSet.delete(cycleNumber);
      }
      return newSet;
    });
  };

  // 新しいサイクルが完了した時に自動的に表示リストに追加
  useEffect(() => {
    if (resultHistory.length > 0) {
      const latestCycle = resultHistory[resultHistory.length - 1];
      setVisibleCycles(prev => {
        const newSet = new Set(prev);
        newSet.add(latestCycle.cycleNumber);
        return newSet;
      });
    }
  }, [resultHistory]);

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

  // 開く時にランキングも取得
  const handleOpenResultUI = () => {
    setOpenResultUI(true);
    fetchRankingExtended(); // ← こちらに変更
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "StartCompare",
        timestamp: new Date().toISOString()
      }));
    }
  };

  // resultHistory or globalRankingRows が変化したら再計算
  useEffect(() => {
    if (!resultHistory.length) return;

    // 1) 自分の各サイクルの平均値を計算
    const averagesPerCycle = {};
    resultHistory.forEach(cycle => {
      averagesPerCycle[cycle.cycleNumber] = getCycleAverages(cycle);
    });
    setCycleAverages(averagesPerCycle);

    // 2) ランキング母集団を組み立てる
    //    可能なら /ranking の全参加者を使い、ダメなら自分のサイクル内で暫定ランキング
    const lowerIsBetterMap = Object.fromEntries(RANK_METRICS.map(m => [m.key, m.lowerIsBetter]));

    // (A) /ranking が使える場合の例：res.data の各行に各指標の平均値がある想定
    //     例 { user_name, cycle_number, FloodDamage_avg, EcosystemLevel_avg, CropYield_avg, MunicipalCost_avg }
    //     ※ API 仕様が違う場合はここを合わせてください。
    let population = [];
    if (Array.isArray(globalRankingRows) && globalRankingRows.length > 0) {
      population = globalRankingRows.map((row, idx) => ({
        id: `global-${idx}`,
        user: row.user_name ?? '',
        cycle: row.cycle_number ?? null,
        values: {
          'Flood Damage':    row.FloodDamage_avg ?? row['Flood Damage'] ?? null,
          'Ecosystem Level': row.EcosystemLevel_avg ?? row['Ecosystem Level'] ?? null,
          'Crop Yield':      row.CropYield_avg ?? row['Crop Yield'] ?? null,
          'Municipal Cost':  row.MunicipalCost_avg ?? row['Municipal Cost'] ?? null,
        }
      }));
    } else {
      // (B) フェイルセーフ：自分のサイクルだけで暫定ランキング
      population = resultHistory.map(cycle => ({
        id: `self-${cycle.cycleNumber}`,
        cycle: cycle.cycleNumber,
        values: averagesPerCycle[cycle.cycleNumber]
      }));
    }

    // 3) 母集団に対する順位表（id→各指標rank）を計算
    const ranksAll = calcRanks(population, lowerIsBetterMap);

    // 4) 各サイクルの順位を抜き出す
    //    - /ranking を使っている時：自分のサイクル値（averagesPerCycle）を母集団に追加して順位を再計算してもOK
    //      →ここでは簡潔化のため、「自サイクルを母集団に追加して」評価します。
    const finalCycleRanks = {};
    resultHistory.forEach(cycle => {
      const selfItem = { id: `self-cycle-${cycle.cycleNumber}`, values: averagesPerCycle[cycle.cycleNumber] };

      // 自分のサイクルを入れた母集団を組み直して順位算出
      const merged = [...population, selfItem];
      const r = calcRanks(merged, lowerIsBetterMap);
      finalCycleRanks[cycle.cycleNumber] = r[selfItem.id]; // { 'Flood Damage': {rank,total}, ... }
    });

    setCycleRanks(finalCycleRanks);
  }, [resultHistory, globalRankingRows]);


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

    // --- プロット属性変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "ScatterAttribute",
        name: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
  };

  const handleOpenSettings = () => {
    setOpenSettingsDialog(true);
  };

  const handleCloseSettings = () => {
    setOpenSettingsDialog(false);
  };

  // 年次選択（入力履歴テーブルの年次フィルター）変更時のハンドラ
  const handleYearFilterChange = (event) => {
    setSelectedYearFilter(event.target.value);

    // --- 年次選択変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "InputHistoryYearFilter",
        value: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
  };
  // サイクル選択（入力履歴テーブルのサイクルフィルター）変更時のハンドラ
  const handleCycleFilterChange = (event) => {
    setSelectedCycleFilter(event.target.value);

    // --- サイクル選択変更ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "InputHistoryCycleFilter",
        value: event.target.value,
        cycle: currentCycle,
        timestamp: new Date().toISOString()
      }));
    }
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

  // Planting Historyの更新（追加）
  const updatePlantingHistory = (year, amount) => {
    setCurrentValues(prev => {
      const updatedHistory = {
        ...(prev.planting_history || {}),  // 以前の履歴を残す
        [year]: amount                     // 新しい年を追加または更新
      };
      const updated = {
        ...prev,
        planting_history: updatedHistory
      };

      console.log("🌱 planting_history 更新:", updatedHistory);
      console.log("🔁 全currentValuesRef:", updated);

      currentValuesRef.current = updated;
      return updated;
    });
  };


  // Model Descriptionボタン押下時のハンドラ
  const handleOpenFormulaModal = () => {
    setOpenFormulaModal(true);
    // --- 「MODEL DESCRIPTION」ボタン押下ログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "OpenModelDescription",
        timestamp: new Date().toISOString()
      }));
    }
    // -------------------------------------------------------------
  };
  // Model Descriptionダイアログを閉じたときのハンドラ
  const handleCloseFormulaModal = () => {
    setOpenFormulaModal(false);
    // --- 「MODEL DESCRIPTION」ダイアログを閉じたログをWebSocketで送信 ---
    if (wsLogRef.current && wsLogRef.current.readyState === WebSocket.OPEN) {
      wsLogRef.current.send(JSON.stringify({
        user_name: userName,
        mode: chartPredictMode,
        type: "CloseModelDescription",
        timestamp: new Date().toISOString()
      }));
    }
    // -------------------------------------------------------------
  };


  const updateCurrentValues = (newDict) => {
    console.log("更新されるnewDict:", newDict);
    const updated = {
      temp: newDict['Temperature (℃)'],
      precip: newDict['Precipitation (mm)'],
      municipal_demand: newDict['Municipal Demand'],
      available_water: newDict['available_water'],
      crop_yield: newDict['Crop Yield'],
      hot_days: newDict['Hot Days'],
      extreme_precip_freq: newDict['Extreme Precip Frequency'],
      ecosystem_level: newDict['Ecosystem Level'],
      levee_level: newDict['Levee Level'],                       
      high_temp_tolerance_level: newDict['High Temp Tolerance Level'],
      forest_area: newDict['Forest Area'],                      
      resident_capacity: newDict['Resident capacity'],          
      transportation_level: newDict['transportation_level'],    
      levee_investment_total: newDict['Levee investment total'],
      RnD_investment_total: newDict['RnD investment total'],    
      risky_house_total: newDict['risky_house_total'],          
      non_risky_house_total: newDict['non_risky_house_total'],  
      resident_burden: newDict['Resident Burden'],
      biodiversity_level: newDict['biodiversity_level'],
      planting_history: newDict['planting_history'],
      paddy_dam_area: newDict['paddy_dam_area'],
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
      'planting_trees_amount': [0, 50, 100],
      'dam_levee_construction_cost': [0, 1, 2], // 既に3段階
      'agricultural_RnD_cost': [0, 5, 10],
      'house_migration_amount': [0, 50, 100],
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
      'planting_trees_amount': [0, 50, 100],
      'dam_levee_construction_cost': [0, 1, 2],
      'agricultural_RnD_cost': [0, 5, 10],
      'house_migration_amount': [0, 50, 100],
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

      {/* ★ Flood flash overlay */}
      <Box
        sx={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 9999,
          backgroundColor: flashOn ? 'rgba(255,0,0,0.25)' : 'transparent',
          transition: 'background-color 150ms ease-in-out',
          // ふわっと点滅を強めたい場合は keyframes を使う：
          // animation: flashOn ? 'flashRed 0.7s ease-in-out' : 'none',
        }}
      />

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
        <Button variant="outlined" onClick={handleOpenFormulaModal}>
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
        
        {/* {showResultButton && (
        <Box sx={{ textAlign: 'center', mt: 0 }}>
          <Button
            variant="contained"
            color="success"
            size="large"
            onClick={handleShowResult}
          >
            {t.buttons.viewResults}
          </Button>
        </Box>
      )} */}
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
          <IconButton color="primary" onClick={handleOpenSettings} sx={{ ml: 1 }}>
            <SettingsIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Model Description Dialog */}
      <Dialog open={openFormulaModal} onClose={handleCloseFormulaModal} maxWidth="xl" fullWidth>
        <DialogTitle>Model Description</DialogTitle>
        <DialogContent>
          <FormulaPage />
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Button variant="contained" onClick={handleCloseFormulaModal}>
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
                onChange={(e) => setSelectedMode(e.target.value)}
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
                onChange={(e) => setSelectedMode(e.target.value)}
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
                onChange={(e) => setSelectedMode(e.target.value)}
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
                  <Box sx={{ display:'flex', alignItems:'center', pl:1 }}>
                    <input
                      type="checkbox"
                      checked={showYearlyDots}
                      onChange={(e)=>setShowYearlyDots(e.target.checked)}
                      style={{ marginRight: 8 }}
                    />
                    <Typography variant="body2">
                      {language === 'ja' ? '各年の点を表示（小・同色）' : 'Show yearly dots (small, same color)'}
                    </Typography>
                  </Box>

                </Box>
                
                {/* 散布図 */}
                <Box sx={{ flex: 1, minHeight: 400 }}>
                  <ScatterChart
                    width={600}
                    height={400}
                    series={resultHistory
                      .filter(cycle => visibleCycles.has(cycle.cycleNumber))
                      .flatMap((cycle, cycleIndex) => {
                        const seriesList = [];

                        // ---- (A) 年ごとの小点（薄色・小さめ） ----
                        if (showYearlyDots) {
                          const yearPoints = cycle.simulationData
                            .filter(d =>
                              typeof d[selectedXAxis] === 'number' &&
                              typeof d[selectedYAxis] === 'number'
                            )
                            .map(d => ({ x: d[selectedXAxis], y: d[selectedYAxis] }));

                          if (yearPoints.length > 0) {
                            seriesList.push({
                              data: yearPoints,
                              color: makeColor(cycleIndex, 0.25),  // 同系色・薄め
                              markerSize: 2,                       // 小さく
                              showMark: true,
                              // label: `${t.scatter.cycle} ${cycle.cycleNumber} (years)`,
                            });
                          }
                        }

                        // ---- (B) 既存の平均/特定年の大きめ点（濃色） ----
                        let targetYears;
                        if (selectedPlotAttribute === 'all') {
                          targetYears = [2050, 2075, 2100];
                        } else if (selectedPlotAttribute === 'average') {
                          targetYears = ['average'];
                        } else {
                          targetYears = [parseInt(selectedPlotAttribute)];
                        }

                        const bigPoints = targetYears.map((year) => {
                          let yearData;

                          if (year === 'average') {
                            const valid = cycle.simulationData.filter(d =>
                              typeof d[selectedXAxis] === 'number' &&
                              typeof d[selectedYAxis] === 'number'
                            );
                            if (!valid.length) return null;
                            const avgX = valid.reduce((s, d) => s + d[selectedXAxis], 0) / valid.length;
                            const avgY = valid.reduce((s, d) => s + d[selectedYAxis], 0) / valid.length;
                            yearData = { [selectedXAxis]: avgX, [selectedYAxis]: avgY };
                          } else {
                            const startYear = year - 25;
                            const endYear = year;
                            const valid = cycle.simulationData.filter(d =>
                              d.Year >= startYear && d.Year <= endYear &&
                              typeof d[selectedXAxis] === 'number' &&
                              typeof d[selectedYAxis] === 'number'
                            );
                            if (!valid.length) return null;
                            const avgX = valid.reduce((s, d) => s + d[selectedXAxis], 0) / valid.length;
                            const avgY = valid.reduce((s, d) => s + d[selectedYAxis], 0) / valid.length;
                            yearData = { [selectedXAxis]: avgX, [selectedYAxis]: avgY };
                          }

                          // 年に応じたサイズ・濃さ
                          let markerSize = 6;
                          let alpha = 0.7;
                          if (year !== 'average') {
                            if (year === 2050) { markerSize = 6; alpha = 0.8; }
                            if (year === 2075) { markerSize = 7; alpha = 0.6; }
                            if (year === 2100) { markerSize = 8; alpha = 0.4; }
                          }

                          return {
                            data: [{ x: yearData[selectedXAxis] || 0, y: yearData[selectedYAxis] || 0 }],
                            color: makeColor(cycleIndex, alpha),  // 同系色・濃いめ
                            markerSize,
                            showMark: true,
                            label: `${t.scatter.cycle} ${cycle.cycleNumber}`,
                          };
                        }).filter(Boolean);

                        return [...seriesList, ...bigPoints];
                      })
                    }
                    xAxis={[{
                      label: getLineChartIndicators(language)[selectedXAxis]?.labelTitle || '',
                      min: 0,
                      max: Math.max(...resultHistory.flatMap(cycle =>
                        cycle.simulationData.map(d => d[selectedXAxis] || 0)
                      )) * 1.1
                    }]}
                    yAxis={[{
                      label: getLineChartIndicators(language)[selectedYAxis]?.labelTitle || '',
                      min: 0,
                      max: Math.max(...resultHistory.flatMap(cycle =>
                        cycle.simulationData.map(d => d[selectedYAxis] || 0)
                      )) * 1.1
                    }]}
                    legend={null}
                  />
                </Box>
                
                {/* サイクル表示制御 */}
                <Box sx={{ mt: 2, border: '1px solid #ddd', borderRadius: 1, p: 2 }}>
                  <Typography variant="body2" fontWeight="bold" gutterBottom>
                    {t.scatter.cycleDisplayControl}
                  </Typography>
                  <Box sx={{ 
                    maxHeight: 150, 
                    overflowY: 'auto', 
                    display: 'flex', 
                    flexWrap: 'wrap', 
                    gap: 1 
                  }}>
                    {resultHistory.map((cycle, index) => {
                      const colors = ['#1976d2', '#dc004e', '#388e3c', '#f57c00', '#7b1fa2', '#d32f2f', '#00796b', '#c2185b', '#ffa000', '#0097a7'];
                      const color = colors[index % colors.length];
                      const isVisible = visibleCycles.has(cycle.cycleNumber);
                      
                      return (
                        <Box key={cycle.cycleNumber} sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 1,
                          p: 0.5,
                          borderRadius: 1,
                          backgroundColor: isVisible ? 'rgba(25, 118, 210, 0.1)' : 'transparent'
                        }}>
                          <input
                            type="checkbox"
                            checked={isVisible}
                            onChange={(e) => handleCycleVisibilityChange(cycle.cycleNumber, e.target.checked)}
                            style={{ margin: 0 }}
                          />
                          <Box sx={{ 
                            width: 12, 
                            height: 12, 
                            backgroundColor: color, 
                            display: 'inline-block',
                            borderRadius: '50%'
                          }}></Box>
                          <Typography variant="caption" sx={{ whiteSpace: 'nowrap' }}>
                            {t.scatter.cycle} {cycle.cycleNumber}
                          </Typography>
                        </Box>
                      );
                    })}
                  </Box>
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
                </Box>
              </Box>
              
              {/* 右側：入力履歴テーブル */}
              <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Typography variant="h6" gutterBottom>
                  {t.scatter.inputHistory}
                </Typography>
                {/* 最新サイクルランキング（コンパクト表示） */}
                {latestCycleNumber && latestRanks && (
                  <Box sx={{
                    mb: 1.5,
                    p: 1,
                    border: '1px solid #e0e0e0',
                    borderRadius: 1,
                    backgroundColor: '#fafafa'
                  }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
                      {language === 'ja' ? `サイクル ${latestCycleNumber} の順位` : `Ranks of Cycle ${latestCycleNumber}`}
                    </Typography>

                    {/* 1行ずつ短く出す（例：洪水被害（2位/4人）） */}
                    {RANK_METRICS.map(m => (
                      <Typography key={m.key} variant="body2" sx={{ lineHeight: 1.4 }}>
                        {language === 'ja'
                          ? `${m.ja}（${latestRanks[m.key]}位/${totalCycles}人）`
                          : `${m.key} (${latestRanks[m.key]}/${totalCycles})`}
                      </Typography>
                    ))}
                  </Box>
                )}
                {/* 年次・サイクル・ソートセレクトバー */}
                <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                  <FormControl sx={{ minWidth: 120 }}>
                    <InputLabel>{t.scatter.yearFilter}</InputLabel>
                    <Select
                      value={selectedYearFilter}
                      label={t.scatter.yearFilter}
                      onChange={handleYearFilterChange}
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
                      onChange={handleCycleFilterChange}
                    >
                      <MenuItem value="all">{t.scatter.allCycles}</MenuItem>
                      {/* サイクル番号リストを動的に生成 */}
                      {resultHistory.map(cycle => (
                        <MenuItem key={cycle.cycleNumber} value={cycle.cycleNumber}>{t.scatter.cycle} {cycle.cycleNumber}</MenuItem>
                      ))}
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
                          {/* <TableCell>{t.sliders.transportation}</TableCell> */}
                          <TableCell>{t.sliders.agriculturalRnD}</TableCell>
                          <TableCell>{t.sliders.capacityBuilding}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {resultHistory.flatMap((cycle, cycleIndex) =>
                          cycle.inputHistory
                            .filter(input =>
                              (selectedYearFilter === 'all' || input.year === Number(selectedYearFilter)) &&
                              (selectedCycleFilter === 'all' || cycle.cycleNumber === Number(selectedCycleFilter))
                            )

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
              src="/system_dynamics.png"
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
              {decisionVar.year - 1} {t.chart.weatherCondition}
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
                onChange={(event, newValue) => {
                  updateDecisionVar('planting_trees_amount', newValue);
                  updatePlantingHistory(decisionVar.year, convertDisplayToBackendValue('planting_trees_amount', newValue));
                }}
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

export default App;