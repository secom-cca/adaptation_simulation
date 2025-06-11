# README

This simulation program is a tool designed to analyze future scenarios by adjusting decision variables while considering trends and uncertainties in climate change. It supports two modes of interaction:

* **Streamlit-based interface**
* **React-based frontend (frontend/src/App.js)**

---

## How to Use

### ✳️ Option 1: Streamlit-based UI

### 1. Select Simulation Mode

From the sidebar, choose one of the following under **"Select Simulation Mode"**:

* **Monte Carlo Simulation Mode**
* **Sequential Decision-Making Mode**

### 2. Enter Scenario Name

Input a name for saving the scenario. For example: `Scenario 1`

### 3. Set Decision Variables

#### For Monte Carlo Simulation Mode

* In **"Decision Variables"**, set the following for each period:

#### For Sequential Decision-Making Mode

* Input the decision variables for the upcoming years via the sidebar sliders.

### 4. Run the Simulation

* Click **"Start Simulation"** or **"Next"**, depending on the mode.

### 5. Review & Save Results

* Graphs will visualize the results.
* Click **"Save Scenario"** to store the scenario for comparison.

### 6. Compare & Export

* Compare multiple scenarios in scatter plots.
* Export results via the **"Data Export"** section.

---

### ✳️ Option 2: React-based UI (`frontend/src/App.js`)

This option allows you to use a modern web interface built with React.

### 1. Launch the Backend API

Make sure the FastAPI backend is running.

```bash
# from the root or backend/ directory
uvicorn backend.main:app --reload
```

> Default port: `http://localhost:8000`

You must keep this running while using the frontend.

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Start the Frontend App

```bash
npm start
```

> This will open the React app at `http://localhost:3000`

### 4. Use the Web Interface

* The UI mimics the Streamlit version but uses REST API to communicate with the backend.
* You can set simulation parameters, run scenarios, view results, and compare/export data.

---

## Notes

* **Session Maintenance**: Reloading the browser may reset session state in Streamlit. Use scenario save/export features as needed.
* **Simulation Reset**: In Streamlit, use the “Reset Simulation” button to start over.
* **Performance**: Large numbers of simulations in Monte Carlo mode will increase computation time. Adjust accordingly.
* **Backend Requirement (React Mode)**: The React frontend requires the FastAPI backend (`backend/main.py`) to be running.

---

## Required Libraries

### Backend (Common to Both UIs)

* Python 3.x
* `streamlit`
* `fastapi`
* `uvicorn`
* `pandas`
* `numpy`
* `plotly`

Install via:

```bash
pip install -r requirements.txt
```

or

```bash
poetry install
```

### Frontend (`frontend/`)

* Node.js (v16+)
* `npm` or `yarn`

---

## How to Run

### ▶ Streamlit Version

```bash
streamlit run main.py
```

or

```bash
poetry run streamlit run main.py
```

### ▶ React + FastAPI Version

```bash
# In one terminal:
uvicorn backend.main:app --reload

# In another terminal:
cd frontend
npm install
npm start
```

了解しました。Intel RealSense を使用する場合に必要な `frontend/ws_server.js` の実行についても明記した、**最終版の README 改訂（該当セクションのみ）** を以下に示します。

---

### 🎥 Optional: Integration with Intel RealSense (`realsense.py` + `ws_server.js`)

You can optionally enable **Intel RealSense camera** integration for gesture- or motion-based control of the simulation interface.

#### 🔧 Requirements

* Intel RealSense Depth Camera (e.g., D435, D455)
* [librealsense](https://github.com/IntelRealSense/librealsense)
* Python package: `pyrealsense2`

Install:

```bash
pip install pyrealsense2
```

#### ▶ How to Run (RealSense Mode)

1. **Start the backend (FastAPI):**

```bash
uvicorn backend.main:app --reload
```

2. **Start the RealSense script:**

```bash
python backend/utils/realsense.py
```

3. **Start the WebSocket relay server (`frontend/ws_server.js`):**

```bash
cd frontend
node ws_server.js
```

> This server bridges `realsense.py` and the React frontend using WebSocket for real-time communication.

4. **Start the frontend app:**

```bash
npm start
```

> React will listen to RealSense input via WebSocket and trigger UI updates or policy changes.

#### 🔗 Integration Flow

```text
Intel RealSense (Depth Input)
        ↓
  realsense.py (Python)
        ↓
  WebSocket (ws_server.js)
        ↓
  React frontend (App.js)
```

#### 💡 Notes

* Ensure all 3 components are running simultaneously:

  * `backend/main.py` (FastAPI)
  * `backend/utils/realsense.py`
  * `frontend/ws_server.js`
* `realsense.py` sends recognized gestures or coordinates to the WebSocket server.
* The frontend listens and updates UI accordingly (e.g., adjust sliders, trigger simulation).

> This is an **optional and experimental** feature — not required for core functionality.

---

## License

This project is licensed under the MIT License.