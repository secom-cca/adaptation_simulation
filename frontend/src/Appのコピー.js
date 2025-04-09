import React, { useState } from "react";
import Button from '@mui/material/Button';
import axios from "axios";
import { Line } from "react-chartjs-2";

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

  return (
    <div style={{ margin: "20px" }}>
      <h1>Climate Simulation Frontend</h1>

      <div style={{ marginBottom: 20 }}>
        <label>シナリオ名: </label>
        <input
          type="text"
          value={scenarioName}
          onChange={(e) => setScenarioName(e.target.value)}
          style={{ marginRight: 20 }}
        />
        <label>モンテカルロ回数: </label>
        <input
          type="number"
          value={numSimulations}
          onChange={(e) => setNumSimulations(e.target.value)}
          style={{ width: "80px" }}
        />
      </div>

      <Button onClick={handleSimulate} disabled={loading}>
        {loading ? "実行中..." : "シミュレーション開始"}
      </Button>

      <Button onClick={handleCompareScenarios} style={{ marginLeft: 10 }}>
        シナリオ比較
      </Button>

      <button onClick={handleDownloadCSV} style={{ marginLeft: 10 }}>
        CSVダウンロード
      </button>

      <Button variant="contained">Hello world</Button>;

      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* 結果があればグラフを表示 */}
      {simulationData.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h2>Simulation Results (Sample: Temperature, Simulation=0)</h2>
          <div style={{ width: "800px", height: "400px" }}>
            <Line data={chartData} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
