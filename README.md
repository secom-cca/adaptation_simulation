# README

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
cd frontend
python realsense.py
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
* Candidate strategy definition as a ladder of policies with trigger maps
* Multi-scenario evaluation with scorecards (robustness, NPV of costs/damages, ecosystem levels, yields, etc.)
* Visualization suite:
> * Pathway composition (stacked policy share over time)
> * Radar charts for candidate comparison (normalized 0–100)
> * Metro map: policy sequences across time buckets, showing transitions as subway-like lines
>> * Export of per-scenario and aggregated scorecards to CSV
>> * Session persistence: simulation results survive UI changes (e.g. changing dropdowns) until explicitly reset

### Usage

```bash
streamlit run dapp_app.py
```

In the web UI:
1. Configure thresholds for evaluation metrics
2. Define candidate pathways (e.g., Nature-first, Engineering-first, etc.)
3. Select RCP scenario and simulation settings
4. Run ▶️ Run DAPP (Monte Carlo)
5. Explore results in visualizations:
- Pathway composition
- Radar chart
- Metro map
6. Export results to CSV if needed

Note: Results are cached in st.session_state. They remain visible until you press 🧹 Clear results.

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