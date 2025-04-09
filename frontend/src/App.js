import React, { useState, useRef } from "react";
import { Alert, AlertTitle, Box, Button, Slider, Stack, Typography, Paper } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Gauge } from '@mui/x-charts/Gauge';
import { LineChart } from '@mui/x-charts/LineChart';
import { ThunderstormOutlined, TsunamiOutlined, WbSunnyOutlined } from '@mui/icons-material';
import axios from "axios";

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

function App() {
  // シミュレーション実行用のステート
  const [scenarioName, setScenarioName] = useState("シナリオ1");
  const [numSimulations, setNumSimulations] = useState(50);
  const [numYear, setNumYear] = useState(2025);
  const intervalRef = useRef(null);
  const isRunningRef = useRef(false);
  const [numA, setNumA] = useState(20)
  const [testData, setTestData] = useState([[], []])
  const [simulationData, setSimulationData] = useState([]); // 結果格納

  // ロード中やエラー表示用
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 単純な例として、10年ごとの意思決定変数を固定で使う
  // 実際にはユーザー入力フォームを作ったり、Table コンポーネントで編集したりします。
  const defaultDecisionVars = [
    { year: 2021, irrigation_water_amount: 100, released_water_amount: 100, levee_construction_cost: 0, agricultural_RnD_cost: 3 },
    { year: 2031, irrigation_water_amount: 100, released_water_amount: 100, levee_construction_cost: 2, agricultural_RnD_cost: 3 },
    { year: 2041, irrigation_water_amount: 80, released_water_amount: 120, levee_construction_cost: 5, agricultural_RnD_cost: 5 },
    // ... 必要に応じて追加
  ];

  // (A) シミュレーション実行ハンドラ
  const handleSimulate = async () => {
    setLoading(true);
    setError("");
    setSimulationData([]);

    try {
      // /simulate に POST するパラメータ
      const body = {
        scenario_name: scenarioName,
        mode: "Monte Carlo Simulation Mode",  // または "Sequential Decision-Making Mode"
        decision_vars: defaultDecisionVars,
        num_simulations: Number(numSimulations),
      };

      // axios でリクエスト
      const resp = await axios.post(`${BACKEND_URL}/simulate`, body);
      console.log("API Response:", resp.data);
      // resp.data はバックエンドの SimulationResponse (scenario_name, data)
      if (resp.data && resp.data.data) {
        setSimulationData(resp.data.data);
      }
    } catch (err) {
      console.error(err);
      setError("シミュレーションに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleClickCalc = () => {
    if (isRunningRef.current) return; // 実行中なら無視

    isRunningRef.current = true;
    let count = 0;
    let nextYear = numYear

    intervalRef.current = setInterval(() => {
      setNumYear((prev) => prev + 1);
      count += 1;
      nextYear += 1;

      if (count >= 10) {
        clearInterval(intervalRef.current);
        isRunningRef.current = false;
      }

      // 利害関係者の評価の変動
      const randomNum = Math.floor(Math.random() * 21) - 10;
      setNumA(randomNum + numA)

      // グラフの評価の変動
      setTestData(prev => {
        const newData = [...prev];
        newData[0] = [...newData[0], nextYear];
        newData[1] = [...newData[1], Math.floor(Math.random() * 10)]
        return newData;
      });

    }, 750);
  }

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

  const DemoPaper = styled(Paper)(({ theme }) => ({
    width: '100%',
    height: '100%',
    padding: theme.spacing(2),
    ...theme.typography.body2,
    textAlign: 'center',
  }));








  return (
    <Box sx={{ padding: 4, backgroundColor: '#f5f7fa', minHeight: '100vh' }}>
      {/* ヘッダー */}
      <Typography variant="h4" gutterBottom>
        Climate Simulation Frontend
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <h2>{numYear}年</h2>
        <Button variant="contained" color="primary" onClick={handleClickCalc}>
          +10年進める
        </Button>
      </Box>


      {error && (
        <Typography color="error" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}

      {/* メインレイアウト */}
      <Box sx={{ display: 'flex', width: '100%', mt: 4, gap: 3 }}>
        {/* 左側：画像＋スライダー */}
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
              src="/causal_loop_diagram.png"
              alt="サンプル画像"
              style={{ width: '100%', display: 'block', height: 'auto' }}
            />

            <Box
              sx={{
                position: 'absolute',
                top: '58.5%',
                left: '67.3%',
                transform: 'translate(-50%, -50%)',
                width: '10%',
                backgroundColor: 'rgba(255, 255, 255, 0.8)',
                padding: '8px',
                borderRadius: '8px',
                boxShadow: 2,
              }}
            >
              <Slider
                defaultValue={30}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => { setNumA(newValue); }}
              />
            </Box>
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
              利害関係者の評価
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 2 }}>
              {/* 各ゲージ */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>政府関係者</Typography>
                <Gauge width={100} height={100} value={Math.ceil(Math.abs(100 - numA / 2))} startAngle={-90} endAngle={90} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>自治体コスト</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>農業関係者</Typography>
                <Gauge width={100} height={100} value={Math.ceil(Math.abs(numA + numA / 2))} startAngle={-90} endAngle={90} valueMax={100} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>収穫量</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>住民</Typography>
                <Gauge width={100} height={100} value={Math.ceil(Math.abs(numA + numA / 4))} startAngle={-90} endAngle={90} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>洪水リスク</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>環境団体</Typography>
                <Gauge width={100} height={100} value={Math.ceil(Math.abs(60 - numA / 2))} startAngle={-90} endAngle={90} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>環境影響</Typography>
              </Box>
            </Box>
          </Box>


          {/* グラフ */}
          <LineChart
            xAxis={[
              {
                data: testData[0],
                label: 'Years',
                scaleType: 'linear',
                tickMinStep: 1,
                showGrid: true,
              },
            ]}
            yAxis={[
              {
                label: '社会全体の収支など？',
                showGrid: true,
              },
            ]}
            series={[
              {
                data: testData[1],
              },
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
        </Paper>
      </Box>
      <p>テスト↓ 確率で発生した場合に表示するイメージ</p>
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
      </Stack>

    </Box >
  );
}

export default App;
