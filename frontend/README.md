# README

This simulation platform allows you to explore future climate adaptation scenarios using either a **Streamlit-based interface** or a **React-based frontend**. It supports policy simulation, Monte Carlo analysis, and optional integration with **Intel RealSense** sensors for gesture-based control.

---

## 🔧 Project Structure

```
.
├── streamlit_main.py                 ← Streamlit entry point
├── backend/
│   ├── main.py                       ← FastAPI backend entry point
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
poetry run streamlit run streamlit_main.py
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

## 🪪 License

This project is licensed under the MIT License.