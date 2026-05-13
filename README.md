# README

## OpenLab-version: frontend-new ワークショップ版

`OpenLab-version` ブランチでは、既存の `frontend` とは別に `frontend-new` を追加しています。明日のワークショップではこのブランチを使い、結果が問題なければ後から `main` へマージする想定です。

### 起動方法

1. バックエンドを起動します。

```bash
cd backend
python main.py
```

2. 別ターミナルで `frontend-new` を起動します。

```bash
cd frontend-new
npm install
npm run dev
```

`frontend-new` は Vite 版の UI で、既存の React UI とは別ルートとして管理しています。

### 予算制約ルール

政策スライダーの見た目は常に `0` から `10` のままです。ただし、使える政策ポイントを超える入力は内部で自動的に切り詰めます。

* 弱 = `0`
* 標準 = `5`
* 強 = `10`

25 年ごとの政策ポイントは、直前 25 年間の結果に応じて減少します。

* 洪水被害額が `2,000,000 USD` 増えるごとに、使える政策ポイントが `1` 減少します。
* 25 年間で住宅移転を累計 `5` ポイント実行するごとに、使える政策ポイントが `1` 減少します。
* `Advance 25 Years` 後は、政策スライダーをすべて `0` に戻します。
* 予算ポイントの減少は累計ではなく、各 25 年ごとに判定します。

### 結果比較

最終結果画面から、政策なしのベースラインおよび保存済みの他グループ結果と比較できます。ベースラインは常に次の固定値として表示します。

* 累計洪水被害額: `43.6億円`
* 最終収穫量: `1628`
* 最終生態系レベル: `71.6`
* 平均住宅負担: `6055`

他グループの結果は、最終評価画面に到達した時点で `backend/data/comparison_results.tsv` に保存されます。このファイルはローカル実行時の生成データなので Git 管理対象外です。

### ランダム性

シミュレーション本体、政策影響、予測に関わる乱数は固定シードで再現可能にしています。ただし、生成 AI ペルソナの年齢・役割選択だけはランダムのままにしています。

---

This simulation platform allows you to explore future climate adaptation scenarios using either a **Streamlit-based interface** or a **React-based frontend**. It supports policy simulation, Monte Carlo analysis, and optional integration with **Intel RealSense** sensors for gesture-based control.

---

## 🔧 Project Structure

```
.
├── main.py                          ← Run each by streamlit 
├── dapp_app.py                      ← Run DAPP by streamlit 
entry point
├── backend/
│   ├── main.py                      ← FastAPI backend entry point
│   └── src/
│       └── simulation.py            ← Core simulation logic
├── frontend/
│   ├── src/
│   │   └── App.js                   ← React frontend app
│   ├── realsense.py                 ← RealSense input processing (Python)
│   └── ws_server.js                 ← WebSocket server (Node.js)
```

---

## 🚀 Usage Options

### Option 1: Streamlit-based UI

#### ▶ How to Run

1. Install dependencies:

```bash
poetry install
```

2. Start Streamlit app:

```bash
poetry run streamlit run main.py
```

> Access at: `http://localhost:8501`

#### 💡 Features

* Fully self-contained (no backend server required)
* Supports Monte Carlo and Sequential Decision-Making modes
* Interactive sliders and tables
* Graphical result visualization
* Scenario saving, comparison, and export

---

### Option 2: React + FastAPI Interface

#### ▶ How to Run (without RealSense)

1. **Start the backend server** in one terminal:

```bash
cd backend
python main.py
```

> Runs FastAPI at `http://localhost:8000`

2. **Start the frontend app** in another terminal:

```bash
cd frontend
npm install       # only once
npm start
```

> Runs React at `http://localhost:3000`

#### 💡 Features

* Modern web UI
* Uses REST API to communicate with backend
* Suitable for advanced browser interactions and extensibility

---

### Option 3: React + FastAPI + RealSense (Optional)

You can enhance the React UI with **gesture or motion input** via Intel RealSense.

#### ▶ Additional Setup

In addition to the above (React + FastAPI), run the following in **two more terminals**:

3. **Start RealSense input handler** (Python):

```bash
cd camera
python realsense_bridge.py
```

4. **Start WebSocket relay server** (Node.js):

```bash
cd frontend
node ws_server.js
```

#### 💡 How It Works

```text
Intel RealSense Camera
        ↓
  realsense.py (Python)
        ↓
  ws_server.js (WebSocket relay)
        ↓
  React App (subscribes via WebSocket)
```

This setup enables real-time control (e.g., simulation execution, parameter tuning) through physical gestures.

---

## 📦 Dependencies

### Python (Backend + Streamlit)

* `streamlit`
* `fastapi`
* `uvicorn`
* `numpy`
* `pandas`
* `plotly`
* (optional) `pyrealsense2` — for RealSense integration

Install via:

```bash
poetry install
```

### JavaScript (Frontend)

* Node.js v16+
* npm or yarn
* `react`, `axios`, etc.

Install via:

```bash
cd frontend
npm install
```

---

## 📁 Data Flow Overview

```
[Decision Input] → [Backend: simulation.py] → [Result JSON]
                                   ↑
         Streamlit or React        |
                    ←── Visualization & Export
```

---

## 📝 Notes

* Use **Streamlit** for fast prototyping or local analysis.
* Use **React + FastAPI** for more interactive, customizable deployments.
* RealSense is entirely **optional**, and not required for core simulations.
* Make sure to keep the backend server running when using React.

---

## 🚀 DAPP Pathway Builder Simulator

This project implements a Dynamic Adaptive Policy Pathways (DAPP) tool for climate adaptation planning, based on a long-term simulation of socio-environmental systems. It uses:
+ backend/src/simulation.py: simulation engine (yearly climate, agriculture, flood, ecosystem, migration, R&D, etc.)
+ backend/config.py: configuration of parameters, default values, RCP climate scenarios
+ backend/src/utils.py: utilities for indicators, scaling, plots
+ dapp_app.py: Streamlit front-end for interactively constructing and visualizing adaptive pathways

### Features

* Monte Carlo simulation of policies under uncertainty (temperature, precipitation, flood events, demand, etc.)
* Adaptive pathway detection using threshold exceedance (ATP: Adaptation Tipping Points)
* Policy switching modes:
  * `Reactive`: uses `Escalation ladder` and `Trigger → policy mapping`
  * `Anticipatory`: chooses from all policy primitives via lookahead optimization
* Two-layer regime mode:
  * Regime shift toggles only the `Crop Yield` constraint ON/OFF
  * toggle probability is `1 / X` per year (`metric_toggle_interval_years`)
  * optional cooldown after each exercise (`cooldown_years`)
* Multi-scenario evaluation with scorecards (robustness, NPV/cumulative costs, ecosystem levels, yields, etc.)
* Visualization suite:
> * Pathway composition (stacked policy share over time)
> * Regime composition (stacked regime share over time)
> * Threshold satisfaction share over time + final-year score table
> * Cost time series (mean across scenarios) + period total summary
> * Metro map: policy/regime sequences across time buckets, showing transitions as subway-like lines
>> * Export of per-scenario and aggregated scorecards to CSV
>> * Session persistence: simulation results survive UI changes until recomputed with `Run DAPP`

### Usage

```bash
streamlit run dapp_app.py
```

In the web UI:
1. Configure thresholds for evaluation metrics
2. Select policy switching mode (`Reactive` or `Anticipatory`)
3. Edit policy primitives
4. If `Reactive`, configure escalation ladder and trigger mapping
5. Select RCP and simulation settings
6. Run ▶️ Run DAPP (Monte Carlo)
7. Explore results in visualizations (composition, thresholds, costs, metro maps)
8. Export results to CSV if needed

Note: Results are stored in `st.session_state` and remain visible until you rerun the simulation.

---

### Next to do
#### High-priority
* Highlight ATP (Adaptation Tipping Point) years in pathway visualizations (e.g., markers in Metro map)
* Scenario grouping & filtering in the UI (e.g., by RCP, by cost level)
* Improve Metro map readability: allow Sankey/alluvial diagrams for policy flows
* User-defined candidates via UI (currently defined in code as CANDIDATES list)

#### Medium-term

* Add Monte Carlo distribution visualizations (uncertainty bands in radar, violin plots)
* Incorporate multi-criteria decision analysis (MCDA) scoring schemes
* Add export to PDF/LaTeX with pathway diagrams and scorecards

#### Long-term

* Integrate with external databases (JMA, Suimon DB, etc.) for real hydrological data
* Support interactive workshops with multiple participants selecting strategies live
* Link with Bayesian causal models for uncertainty propagation

---

## 🪪 License

This project is licensed under the MIT License.
