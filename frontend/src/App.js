import React, { useState, useRef, useEffect } from "react";
import { Alert, AlertTitle, Box, Button, Dialog, DialogTitle, DialogContent, Grid, IconButton, Slider, Stack, styled, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Paper } from '@mui/material';
import { LineChart, ScatterChart, Gauge } from '@mui/x-charts';
import { ThunderstormOutlined, TsunamiOutlined, WbSunnyOutlined } from '@mui/icons-material';
import InfoIcon from '@mui/icons-material/Info';
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

// 各種設定

const LINE_CHART_ITEM = "Crop Yield"

function App() {
  // シミュレーション実行用のステート
  const [scenarioName, setScenarioName] = useState("シナリオ1");
  const [numSimulations, setNumSimulations] = useState(1);
  const intervalRef = useRef(null);
  const isRunningRef = useRef(false);
  const [numA, setNumA] = useState(20)
  const [chartPredictData, setChartPredictData] = useState([[], []]); // [0]が初期値予測 [1]が下限値予測、[2]が上限値予測
  const [openResultUI, setOpenResultUI] = useState(false);
  const [decisionVar, setDecisionVar] = useState({
    year: 2026,
    planting_trees_amount: 100.,   // 植林・森林保全
    house_migration_amount: 100.,  // 住宅移転・嵩上げ
    dam_levee_construction_cost: 0., //ダム・堤防工事
    paddy_dam_construction_cost: 3., //田んぼダム工事
    capacity_building_cost: 3.,   // 防災訓練・普及啓発
    // irrigation_water_amount: 100, // 灌漑水量
    // released_water_amount: 100,   // 放流水量
    transportation_invest: 3,     // 交通網の拡充
    agricultural_RnD_cost: 3,      // 農業研究開発
    cp_climate_params: 4.5 //RCPの不確実性シナリオ
  })
  const [currentValues, setCurrentValues] = useState({
    temp: 15.0,
    precip: 1000.0,
    municipal_demand: 100.0,
    available_water: 1000.0,
    crop_yield: 100.0,
    levee_level: 0.5,
    high_temp_tolerance_level: 0.0,
    hot_days: 30.0,
    extreme_precip_freq: 0.1,
    ecosystem_level: 100.0,
    levee_investment_years: 0,
    RnD_investment_years: 0,
    urban_level: 100.,
    resident_burden: 80.,
    biodiversity_level: 100.,
  })
  const [simulationData, setSimulationData] = useState([]); // 結果格納

  // ロード中やエラー表示用
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // リアルタイム更新用
  const currentValuesRef = useRef(currentValues);
  const decisionVarRef = useRef(decisionVar);

  useEffect(() => {
    currentValuesRef.current = currentValues;
  }, [currentValues]);

  useEffect(() => {
    decisionVarRef.current = decisionVar;
    fetchForecastData();
  }, [decisionVar]);

  // (A) シミュレーション実行ハンドラ
  const handleSimulate = async () => {
    setLoading(true);
    setError("");

    try {
      // /simulate に POST するパラメータ
      console.log("現在の入力:", decisionVarRef.current, currentValuesRef.current)
      const body = {
        scenario_name: scenarioName,
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
        setSimulationData(prev => [...prev, ...resp.data.data]);
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

    while (count < 15) {

      // シミュレーション実行
      await handleSimulate();

      // 次へ
      count += 1;
      nextYear += 1;

      // 現在の年を更新
      updateDecisionVar("year", nextYear);

      // 表示更新のために一時停止（見た目をスムーズに）
      await new Promise(res => setTimeout(res, 750));
    }

    isRunningRef.current = false;
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
        scenario_name: scenarioName,
        mode: "Predict Simulation Mode",  // "Monte Carlo Simulation Mode" または "Sequential Decision-Making Mode"
        decision_vars: [lowerDecisionVar],
        num_simulations: Number(numSimulations),
        current_year_index_seq: currentValuesRef.current
      };

      // axios でリクエスト
      const resp = await axios.post(`${BACKEND_URL}/simulate`, lowerBody);
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
      temp: newDict["Temperature (℃)"],
      precip: newDict["Precipitation (mm)"],
      municipal_demand: newDict["Municipal Demand"],
      available_water: newDict["Available Water"],
      crop_yield: newDict["Crop Yield"],
      // levee_level: newDict[""],
      high_temp_tolerance_level: newDict["High Temp Tolerance Level"],
      hot_days: newDict["Hot Days"],
      extreme_precip_freq: newDict["Extreme Precip Frequency"],
      ecosystem_level: newDict["Ecosystem Level"],
      // levee_investment_years: newDict[""],
      // RnD_investment_years: newDict[""],
      urban_level: newDict['Urban Level'],
      resident_burden: newDict['Resident Burden'],
      biodiversity_level: newDict['Biodiversity Level']
    };
    console.log("更新されるcurrentValues:", updated);
    setCurrentValues(prev => ({ ...prev, ...updated }));
    currentValuesRef.current = { ...currentValuesRef.current, ...updated };
  };

  // chartPredictData[1] のデータを取得
  const xAxisYears = Array.from({ length: 2100 - 2025 + 1 }, (_, i) => 2026 + i);

  const getPredictData = (predicDataArray) => {
    const predictDataMap = new Map();
    if (predicDataArray) { // predicDataArray が存在する場合のみ処理
      predicDataArray.forEach(item => {
        predictDataMap.set(item["Year"], item[LINE_CHART_ITEM]);
      });
    }

    // X軸の各年に対応する温度データの配列を生成（データがない年はnull）
    const formattedPredictData = xAxisYears.map(year => {
      return predictDataMap.has(year) ? predictDataMap.get(year) : null;
    });

    return formattedPredictData
  }






  return (
    <Box sx={{ padding: 2, backgroundColor: '#f5f7fa', minHeight: '100vh' }}>
      {/* ヘッダー */}


      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="h4" gutterBottom>
          気候変動シミュレーション
        </Typography>
        <h2>{decisionVar.year - 1}年</h2>
        <Button variant="contained" color="primary" onClick={handleClickCalc}>
          15年進める
        </Button>
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
        <IconButton color="primary" onClick={handleOpenResultUI}>
          <InfoIcon />
        </IconButton>
      </Box>
      </Box>

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
              src="/causal_loop_diagram.png"
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
              {decisionVar.year - 1}年時点の評価
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: 2 }}>
              {/* 各ゲージ */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>年平均気温</Typography>
                <Gauge width={100} height={100} value={currentValues.temp} valueMax={40} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>℃</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>年平均降水量</Typography>
                <Gauge width={100} height={100} value={currentValues.precip} valueMax={1500} valueMin={500} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>mm</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>住民の負担</Typography>
                <Gauge width={100} height={100} value={currentValues.resident_burden} valueMax={300} />
                <Typography variant="caption" sx={{ mt: '0px', fontSize: '0.75rem', color: 'text.secondary' }}>ー</Typography>
              </Box>

              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mb: 0 }}>生物多様性</Typography>
                <Gauge width={100} height={100} value={currentValues.biodiversity_level} valueMax={120} />
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
                label: '収穫量',
                showGrid: true,
                // min: 10,
                // max: 30
              },
            ]}
            series={[
              {
                data: simulationData.map((row) => row[LINE_CHART_ITEM]),
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
              交通網の充実
              <Slider
                defaultValue={decisionVar.transportation_invest}
                min={0}
                max={9}
                marks={[{ value: 0 }, { value: 3 }, { value: 6 }, { value: 9 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('transportation_invest', newValue)}
              />
            </Box>
          </Grid>
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
              植林・森林保全
              <Slider
                defaultValue={decisionVar.planting_trees_amount}
                min={0}
                max={200}
                marks={[{ value: 0 }, { value: 50 }, { value: 100 }, { value: 150 }, { value: 200 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('planting_trees_amount', newValue)}
              />
            </Box>
          </Grid>
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
              ダム・堤防工事
              <Slider
                defaultValue={decisionVar.dam_levee_construction_cost}
                min={0}
                max={9}
                marks={[{ value: 0 }, { value: 3 }, { value: 6 }, { value: 9 }]}
                step={null}
                aria-label="画像スライダー"
                size="small"
                valueLabelDisplay="auto"
                color="secondary"
                onChange={(event, newValue) => updateDecisionVar('dam_levee_construction_cost', newValue)}
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
              農業研究開発
              <Slider
                defaultValue={decisionVar.agricultural_RnD_cost}
                min={0}
                max={9}
                marks={[{ value: 0 }, { value: 3 }, { value: 6 }, { value: 9 }]}
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
              住宅移転・嵩上げ
              <Slider
                defaultValue={decisionVar.house_migration_amount}
                min={0}
                max={200}
                marks={[{ value: 0 }, { value: 50 }, { value: 100 }, { value: 150 }, { value: 200 }]}
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
              田んぼダム工事
              <Slider
                defaultValue={decisionVar.paddy_dam_construction_cost}
                min={0}
                max={9}
                marks={[{ value: 0 }, { value: 3 }, { value: 6 }, { value: 9 }]}
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
              防災訓練・啓発
              <Slider
                defaultValue={decisionVar.capacity_building_cost}
                min={0}
                max={9}
                marks={[{ value: 0 }, { value: 3 }, { value: 6 }, { value: 9 }]}
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



      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <h2>テスト↓ API周り</h2>
        <Button variant="contained" color="primary" onClick={handleSimulate}>
          simulation
        </Button>
      </Box>

      <p>{simulationData.at(-1)?.["Crop Yield"]}</p>
      <p>{JSON.stringify(simulationData)}</p>

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
