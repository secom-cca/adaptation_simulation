# README

This simulation program is a tool designed to analyze future scenarios by adjusting decision variables while considering trends and uncertainties in climate change and urban water demand. It utilizes Streamlit to provide an interactive user interface.

## How to Use

### 1. Select Simulation Mode

From the sidebar, choose one of the following under "Select Simulation Mode":

- **Monte Carlo Simulation Mode**
- **Sequential Decision-Making Mode**

### 2. Enter Scenario Name

Input a name for saving the scenario. For example: `Scenario 1`

### 3. Set Decision Variables

#### For Monte Carlo Simulation Mode

- In "Decision Variables (Every 10 yrs)", set the following variables for each 10-year period using the DataFrame:
  - Irrigation Water Amount
  - Released Water Amount
  - Levee Construction Cost
  - Agricultural R&D Cost

#### For Sequential Decision-Making Mode

- Input the decision variables for the next 10 years using the sidebar.

### 4. Run the Simulation

- **Monte Carlo Simulation Mode**: Click the "Start Simulation" button.
- **Sequential Decision-Making Mode**: Click the "Next" button. Review the results and adjust decision variables as needed.

### 5. Review Results

- Simulation results will be displayed in graphs.
- In Monte Carlo Simulation Mode, results from each simulation are overlaid to visualize variability.
- In Sequential Decision-Making Mode, results from a single simulation are displayed.

### 6. Save Scenario

- When satisfied with the results, click the "Save Scenario" button to save the scenario.

### 7. Compare Scenarios

- In the "Scenario Comparison" section, select the scenarios you wish to compare.
- Choose variables for the X and Y axes of the scatter plot and compare the scenarios.

### 8. Export Data

- In the "Data Export" section, select the file format.
- Click the "Download" button to download the simulation results.

## Notes

- **Session Maintenance**: Reloading the browser may reset the session state, causing loss of simulation results and saved scenarios. Export data as needed.

- **Simulation Reset**: Use the "Reset Simulation" button if you want to start a new scenario or redo the simulation. Saved scenarios will remain intact.

- **Performance**: Setting a high number of simulations in Monte Carlo Simulation Mode may increase computation time. Choose an appropriate number.

## Required Libraries

- Python 3.x
- Streamlit
- numpy
- pandas
- plotly

## How to Run

1. Install the required libraries:

```bash
pip install streamlit numpy pandas plotly
```

2. In the directory where you saved the script, run the following command:

```bash
streamlit run main.py
```

3. If the browser doesn't open automatically, enter the local host URL displayed in the command line (e.g., `http://localhost:8501`) into your browser to access the application.

4. Or you can use poetry:

```bash
poetry install
poetry run streamlit run main.py
```

## License

This project is licensed under the MIT License.
