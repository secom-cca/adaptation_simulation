# README

This simulation program is a tool designed to analyze future scenarios by adjusting decision variables while considering trends and uncertainties in climate change and urban water demand. It utilizes Streamlit to provide an interactive user interface.

## Features

- **Simulation Mode Selection**:
  - **Monte Carlo Simulation Mode**: Executes numerous simulations at once, considering uncertainties. Decision variables for every 5 years are pre-set, and results can be analyzed using scatter plots and other visualizations.
  - **Sequential Decision Simulation Mode**: Eliminates uncertainties and allows you to adjust decision variables every 5 years while reviewing the results. You can compare results across different scenarios.

- **Adjustment of Decision Variables**:
  - **Monte Carlo Simulation Mode**: Set decision variables for every 5 years collectively using a DataFrame.
  - **Sequential Decision Simulation Mode**: Input decision variables for the next 5 years, adjusting them as you review the results.

- **Setting Trends and Uncertainties**: Adjust trends and uncertainty ranges for temperature, precipitation, extreme precipitation frequency, and urban water demand.

- **Visualization of Simulation Results**: Use graphs and scatter plots to visually inspect the results.

- **Scenario Saving and Comparison**: Save multiple scenarios and compare them based on selected variables.

- **Data Export**: Download simulation results in CSV or Excel format.

## How to Use

### 1. Select Simulation Mode

From the sidebar, choose one of the following under "Select Simulation Mode":

- **Monte Carlo Simulation Mode**
- **Sequential Decision Simulation Mode**

### 2. Enter Scenario Name

Input a name for saving the scenario. For example: `Scenario 1`

### 3. Set Trend and Uncertainty Parameters

- Temperature trend and uncertainty range
- Precipitation trend and uncertainty range
- Extreme precipitation frequency trend and uncertainty range
- Urban water demand growth trend and uncertainty range

Adjust these values using the sliders provided.

### 4. Set Decision Variables

#### For Monte Carlo Simulation Mode

- In "Decision Variables (Every 5 Years)", set the following variables for each 5-year period using the DataFrame:
  - Irrigation Water Amount
  - Released Water Amount
  - Levee Construction Cost
  - Agricultural R&D Cost

#### For Sequential Decision Simulation Mode

- Input the decision variables for the next 5 years using the sidebar.

### 5. Run the Simulation

- **Monte Carlo Simulation Mode**: Click the "Start Simulation" button.
- **Sequential Decision Simulation Mode**: Click the "Next 5 Years" button. Review the results and adjust decision variables as needed.

### 6. Review Results

- Simulation results will be displayed in graphs.
- In Monte Carlo Simulation Mode, results from each simulation are overlaid to visualize variability.
- In Sequential Decision Simulation Mode, results from a single simulation are displayed.

### 7. Save Scenario

- When satisfied with the results, click the "Save Scenario" button to save the scenario.

### 8. Compare Scenarios

- In the "Scenario Comparison" section, select the scenarios you wish to compare.
- Choose variables for the X and Y axes of the scatter plot and compare the scenarios.

### 9. Export Data

- In the "Data Export" section, select the file format (CSV or Excel).
- Click the "Download Data" button to download the simulation results.

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
streamlit run simulation_montecarlo.py
```

3. If the browser doesn't open automatically, enter the local host URL displayed in the command line (e.g., `http://localhost:8501`) into your browser to access the application.

## License

This project is licensed under the MIT License.
