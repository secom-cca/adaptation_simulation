import React, { useState, useRef, useEffect } from "react";
import { Alert, AlertTitle, Box, Button, Dialog, DialogTitle, DialogContent, FormControl, Grid, IconButton, InputLabel, MenuItem, Slider, Stack, Select, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Paper, TextField } from '@mui/material';
import { LineChart, ScatterChart, Gauge } from '@mui/x-charts';
import { Agriculture, Biotech, EmojiTransportation, Flood, Forest, Houseboat, LocalLibrary, Science, ThunderstormOutlined, TsunamiOutlined, WbSunnyOutlined } from '@mui/icons-material';
import InfoIcon from '@mui/icons-material/Info';
import axios from "axios";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import FormulaPage from "./FormulaPage"; // 新ページ

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

const lineChartIndicators = {
  'Crop Yield': { labelTitle: '収穫量', max: 5, min: 0, unit: 'ton/ha' },
  'Flood Damage': { labelTitle: '洪水被害', max: 10000, min: 0, unit: '万円' },
  'Ecosystem Level': { labelTitle: '生態系', max: 100, min: 0, unit: '-' },
  'Urban Level': { labelTitle: '都市利便性', max: 100, min: 0, unit: '-' },
  'Municipal Cost': { labelTitle: '予算', max: 100000, min: 0, unit: '万円' },
  'Temperature (℃)': { labelTitle: '気温', max: 30, min: 10, unit: '℃' }
};
const SIMULATION_YEARS = 25 // 一回のシミュレーションで進める年数を決定する 
const LINE_CHART_DISPLAY_INTERVAL = 100 // ms
const INDICATOR_CONVERSION = {
  'Municipal Cost': 1 / 10000, // 円 → 億円
  'Flood Damage': 1 / 10000, // 円 → 万円
  'Crop Yield': 1 / 1000 // kg → ton（例）
};


function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/formula" element={<FormulaPage />} />
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
  const [openResultUI, setOpenResultUI] = useState(false);
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

  // LineChartの縦軸の変更
  const [selectedIndicator, setSelectedIndicator] = useState('Crop Yield');
  const currentIndicator = lineChartIndicators[selectedIndicator];
  const handleLineChartChange = (event) => {
    setSelectedIndicator(event.target.value);
  };

  const [userName, setUserName] = useState(localStorage.getItem('userName') || '');
  const [openNameDialog, setOpenNameDialog] = useState(!userName);
  const [blockScores, setBlockScores] = useState([]);   // Array<Backend BlockRaw>
  const [ranking,setRanking] = useState([]);
  const [showResultButton, setShowResultButton] = useState(false);
  const [userNameError, setUserNameError] = useState("")

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
        setUserName(userName.trim());
        setOpenNameDialog(false);
        setUserNameError(""); // エラー解除
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
    const storedName = localStorage.getItem('userName');
    if (!storedName || storedName.trim() === '') {
      setOpenNameDialog(true);
    } else {
      setUserName(storedName);
    }
  }, []);

  useEffect(() => {
    // 開発中のみ userName を強制リセット
    if (process.env.NODE_ENV === 'development') {
      localStorage.removeItem('userName');
    }
  
    const storedName = localStorage.getItem('userName');
    if (!storedName || storedName.trim() === '') {
      setOpenNameDialog(true);
    } else {
      setUserName(storedName);
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
    if (isRunningRef.current) return;
    isRunningRef.current = true;

    let nextYear = decisionVar.year;
    let count = 0;

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
    if (nextYear > 2100) {
      setShowResultButton(true);
    }
    
  };

  // decisionVarが変動した際に予測値をリアルタイムで取得する
  const fetchForecastData = async () => {
    try {
      // /simulate に POST するパラメータ
      console.log("現在の入力:", decisionVarRef.current, currentValuesRef.current)

      // 上限予測値の計算
      let upperDecisionVar = { ...decisionVarRef.current };
      upperDecisionVar['cp_climate_params'] = 8.5
      // console.log("上限値のパラメータ：", upperDecisionVar)

      const upperBody = {
        user_name: userName,
        scenario_name: scenarioName,
        mode: "Predict Simulation Mode",  // "Monte Carlo Simulation Mode" または "Sequential Decision-Making Mode"
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
      // console.log("下限値のパラメータ：", lowerDecisionVar)

      const lowerBody = {
        user_name: userName, // ← これを追加
        scenario_name: scenarioName,
        mode: "Predict Simulation Mode",  // "Monte Carlo Simulation Mode" または "Sequential Decision-Making Mode"
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
  };

  const handleCloseResultUI = () => {
    setOpenResultUI(false);
  };

  // (F) パラメータ周りの変更処理
  const updateDecisionVar = (key, value) => {
    setDecisionVar(prev => {
      const updated = { ...prev, [key]: value };
      decisionVarRef.current = updated;
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
      levee_level: newDict['Levee Level'],                          // ← 追加
      high_temp_tolerance_level: newDict['High Temp Tolerance Level'],
      forest_area: newDict['Forest area'],                         // ← 追加
      resident_capacity: newDict['Resident capacity'],             // ← 追加
      transportation_level: newDict['transportation_level'],       // ← 追加
      levee_investment_total: newDict['Levee investment total'],   // ← 追加
      RnD_investment_total: newDict['RnD investment total'],       // ← 追加
      risky_house_total: newDict['risky_house_total'],             // ← 追加
      non_risky_house_total: newDict['non_risky_house_total'],     // ← 追加
      resident_burden: newDict['Resident Burden'],
      biodiversity_level: newDict['biodiversity_level'],           // ← 追加（キー名注意）

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




  return (
    <Box sx={{ padding: 2, backgroundColor: '#f5f7fa', minHeight: '100vh' }}>
      {/* ヘッダー */}


      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h4" gutterBottom>
          気候変動適応策検討シミュレーション
        </Typography>
        <h2>{decisionVar.year - 1}年</h2>
        <Button variant="contained" color="primary" onClick={handleClickCalc}>
          {SIMULATION_YEARS}年進める
        </Button>
        <Link to="/formula">
          <Button variant="outlined">モデルの説明を見る</Button>
        </Link>
        {showResultButton && (
        <Box sx={{ textAlign: 'center', mt: 0 }}>
          <Button
            variant="contained"
            color="success"
            size="large"
            onClick={handleShowResult}
          >
            結果を見る
          </Button>
        </Box>
      )}
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
          <IconButton color="primary" onClick={handleOpenResultUI}>
            <InfoIcon />
          </IconButton>
        </Box>
      </Box>

      <Dialog open={openNameDialog} disableEscapeKeyDown>
        <DialogTitle>お名前を入力してください</DialogTitle>
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
          />
          <Button
            variant="contained"
            fullWidth
            disabled={!userName.trim()}
            onClick={handleUserNameRegister}
            sx={{ mt: 2 }}
          >
            登録
          </Button>
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
              src="/sd_model.png"
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
              {decisionVar.year - 1}年の気象条件と将来影響予測
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 2 }}>
              {/* 各ゲージ */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>年平均気温</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.temp * 100) / 100} valueMax={40} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>℃</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>年平均降水量</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.precip * 10) / 10} valueMax={2000} valueMin={500} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>mm</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>大雨の頻度</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.extreme_precip_freq)} valueMax={10} valueMin={0} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>回/年</Typography>
              </Box>

              {/* <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>収穫量</Typography>
                <Gauge width={100} height={100} value={Math.round(currentValues.crop_yield)} valueMax={5000} valueMin={0}/>
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>ton/ha</Typography>
              </Box> */}

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>住民の負担</Typography>
                <Gauge width={100} height={100} value={currentValues.resident_burden * INDICATOR_CONVERSION["Municipal Cost"]} valueMax={10} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>億円</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>生物多様性</Typography>
                <Gauge width={100} height={100} value={currentValues.ecosystem_level} valueMax={100} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>ー</Typography>
              </Box>
            </Box>
          </Box>


          {/* グラフ */}
          <LineChart
            xAxis={[
              {
                data: xAxisYears,
                label: 'Years',
                scaleType: 'linear',
                tickMinStep: 1,
                showGrid: true,
                min: 2020,
                max: 2100
              },
            ]}
            yAxis={[
              {
                label: `${currentIndicator.labelTitle}（${currentIndicator.unit}）`,
                min: currentIndicator.min,
                max: currentIndicator.max,
                showGrid: true
              },
            ]}
            series={[
              {
                data: simulationData.map((row) => row[selectedIndicator]),
                label: '実測値',
                color: '#ff5722',
                showMark: false,
              },
              {
                data: getPredictData(chartPredictData[1]),
                label: '上限値予測',
                color: '#cccccc',
                lineStyle: 'dashed',
                showMark: false
              },
              {
                data: getPredictData(chartPredictData[0]),
                label: '下限値予測',
                color: '#cccccc',
                lineStyle: 'dashed',
                showMark: false
              }
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
            <InputLabel id="indicator-select-label">縦軸を選択</InputLabel>
            <Select
              labelId="indicator-select-label"
              value={selectedIndicator}
              label="縦軸を選択"
              onChange={handleLineChartChange}
            >
              {Object.keys(lineChartIndicators).map((key) => (
                <MenuItem key={key} value={key}>
                  {lineChartIndicators[key].labelTitle}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Paper>
      </Box>
      <Box style={{ width: '100%' }}>
        <Grid container spacing={2}> {/* spacingでBox間の余白を調整できます */}
          <Grid size={3}>
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
              植林・森林保全
              <Slider
                value={decisionVar.planting_trees_amount}
                min={0}
                max={200}
                marks={[{ value: 0 }, { value: 100 }, { value: 200 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('planting_trees_amount', newValue)}
              />
            </Box>
          </Grid>
          <Grid size={3}>
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
              公共バス
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
              />
            </Box>
          </Grid>
          <Grid size={3}>
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
                河川堤防
              <Slider
                value={decisionVar.dam_levee_construction_cost}
                min={0}
                max={2}
                marks={[{ value: 0 }, { value: 1 }, { value: 2 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('dam_levee_construction_cost', newValue)}
              />
            </Box>
          </Grid><Grid size={3}>
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
              高温耐性品種
              <Slider
                value={decisionVar.agricultural_RnD_cost}
                min={0}
                max={10}
                marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('agricultural_RnD_cost', newValue)}
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
              住宅移転
              <Slider
                value={decisionVar.house_migration_amount}
                min={0}
                max={10}
                marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('house_migration_amount', newValue)}
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
              田んぼダム
              <Slider
                value={decisionVar.paddy_dam_construction_cost}
                min={0}
                max={10}
                marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('paddy_dam_construction_cost', newValue)}
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
              防災訓練・啓発
              <Slider
                value={decisionVar.capacity_building_cost}
                min={0}
                max={10}
                marks={[{ value: 0 }, { value: 5 }, { value: 10 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('capacity_building_cost', newValue)}
              />
            </Box>
          </Grid>
        </Grid>
      </Box>



      {/* <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <h2>[DEBUG] API周り</h2>
        <Button variant="contained" color="primary" onClick={handleSimulate}>
          simulation
        </Button>
      </Box>

      <TableContainer component={Paper} sx={{mt:2}}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>期間</TableCell>
              <TableCell align="right">合計点</TableCell>
              <TableCell align="right">収量</TableCell>
              <TableCell align="right">洪水</TableCell>
              <TableCell align="right">生態系</TableCell>
              <TableCell align="right">都市</TableCell>
              <TableCell align="right">予算</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {blockScores.map((b,i)=>(
              <TableRow key={i}>
                <TableCell>{b.period}</TableCell>
                <TableCell align="right">{b.total_score.toFixed(1)}</TableCell>
                {Object.keys(b.score).map(k=>(
                  <TableCell key={k} align="right">{b.score[k].toFixed(1)}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openResultUI} onClose={handleCloseResultUI} maxWidth="sm" fullWidth>
        <DialogTitle>ランキング</DialogTitle>
        <DialogContent>
          <Table size="small">
            <TableHead><TableRow>
              <TableCell>順位</TableCell><TableCell>ユーザ</TableCell><TableCell align="right">平均点</TableCell>
            </TableRow></TableHead>
            <TableBody>
              {ranking.map(r=>(
                <TableRow key={r.rank}>
                  <TableCell>{r.rank}</TableCell>
                  <TableCell>{r.user_name}</TableCell>
                  <TableCell align="right">{r.total_score.toFixed(1)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog> */}

      {/* <p>{simulationData.at(-1)?.["Crop Yield"]}</p>
      <p>{JSON.stringify(simulationData)}</p> */}

      {/* <p>テスト↓ 確率で発生した場合に表示するイメージ</p>
      <Stack sx={{ width: '100%' }} spacing={2}>
        <Alert
          iconMapping={{
            error: <ThunderstormOutlined fontSize="inherit" />,
          }}
          severity="error"
        >
          <AlertTitle>大雨が降りました</AlertTitle>
          This success Alert uses `iconMapping` to override the default icon.
        </Alert>

        <Alert
          iconMapping={{
            error: <TsunamiOutlined fontSize="inherit" />,
          }}
          severity="error"
        >
          <AlertTitle>高潮が発生しました</AlertTitle>
          This success Alert uses `iconMapping` to override the default icon.
        </Alert>

        <Alert
          iconMapping={{
            error: <WbSunnyOutlined fontSize="inherit" />,
          }}
          severity="error"
        >
          <AlertTitle>高温注意</AlertTitle>
          This success Alert uses `iconMapping` to override the default icon.
        </Alert>
      </Stack> */}

      <Dialog open={openResultUI} onClose={handleCloseResultUI} maxWidth="md" fullWidth>
        <DialogTitle>各シミュレーション結果の比較</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {/* 散布図 */}
            <Box sx={{ flex: 1, minWidth: 300 }}>
              <ScatterChart
                width={400}
                height={300}
                series={[
                  {
                    label: 'シミュレーション結果',
                    data: [
                      { x: 2020, y: 5 },
                      { x: 2025, y: 6 },
                      { x: 2030, y: 8 },
                      { x: 2035, y: 7 },
                      { x: 2040, y: 10 },
                    ],
                  },
                ]}
                xAxis={[{ label: '経済性など' }]}
                yAxis={[{ label: '収穫量など' }]}
              />
            </Box>

            {/* テーブル */}
            <Box sx={{ flex: 1, minWidth: 300 }}>
              <TableContainer component={Paper}>
                <Table size="small" aria-label="散布図データ">
                  <TableHead>
                    <TableRow>
                      <TableCell>年</TableCell>
                      <TableCell align="right">値</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {[
                      { year: 2020, value: 5 },
                      { year: 2025, value: 6 },
                      { year: 2030, value: 8 },
                      { year: 2035, value: 7 },
                      { year: 2040, value: 10 },
                    ].map((row, index) => (
                      <TableRow key={index}>
                        <TableCell>{row.year}</TableCell>
                        <TableCell align="right">{row.value}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </Box>
        </DialogContent>

      </Dialog>

    </Box >
  );
}

export default App;