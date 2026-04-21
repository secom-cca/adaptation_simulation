# Y-Axis Auto-scaling Fix Documentation

## 🔍 **Problem Identified**

The user reported that the Y-axis in the visualization charts was being truncated in some cases, causing data points to be cut off and not visible. This was due to insufficient auto-scaling capabilities.

## 🛠️ **Root Cause Analysis**

### **Issue 1: Fixed Y-axis Range in Line Chart**
- **Location**: `App.js` lines 1656-1657
- **Problem**: Y-axis used fixed min/max values from configuration
- **Code**: 
```javascript
min: getLineChartIndicators(language)[selectedIndicator].min,
max: getLineChartIndicators(language)[selectedIndicator].max,
```

### **Issue 2: Insufficient Buffer in Scatter Plot**
- **Location**: `App.js` lines 1440-1442
- **Problem**: Only 10% buffer, which might not be enough for extreme values
- **Code**:
```javascript
max: Math.max(...resultHistory.flatMap(cycle => 
  cycle.simulationData.map(data => data[selectedYAxis] || 0)
)) * 1.1
```

## ✅ **Solutions Implemented**

### **1. Dynamic Y-axis Range for Line Chart**

**New Implementation** (lines 1656-1677):
```javascript
min: (() => {
  // Calculate actual minimum value from data
  const dataValues = simulationData.map((row) => row[selectedIndicator]).filter(val => val != null);
  const predictValues = chartPredictMode !== 'none' ? 
    chartPredictData.flatMap(data => getPredictData(data)).filter(val => val != null) : [];
  const allValues = [...dataValues, ...predictValues];
  const actualMin = allValues.length > 0 ? Math.min(...allValues) : 0;
  const configMin = getLineChartIndicators(language)[selectedIndicator].min;
  // Use the smaller of actual minimum and config minimum, with 10% buffer
  return Math.min(actualMin * 0.9, configMin);
})(),
max: (() => {
  // Calculate actual maximum value from data
  const dataValues = simulationData.map((row) => row[selectedIndicator]).filter(val => val != null);
  const predictValues = chartPredictMode !== 'none' ? 
    chartPredictData.flatMap(data => getPredictData(data)).filter(val => val != null) : [];
  const allValues = [...dataValues, ...predictValues];
  const actualMax = allValues.length > 0 ? Math.max(...allValues) : 100;
  const configMax = getLineChartIndicators(language)[selectedIndicator].max;
  // Use the larger of actual maximum and config maximum, with 10% buffer
  return Math.max(actualMax * 1.1, configMax);
})(),
```

**Key Features:**
- ✅ **Dynamic calculation** based on actual data values
- ✅ **Includes prediction data** in range calculation
- ✅ **Maintains configuration minimums** as fallback
- ✅ **10% buffer space** above and below data range
- ✅ **Null value filtering** to prevent errors

### **2. Enhanced Scatter Plot Auto-scaling**

**X-axis Enhancement** (lines 1430-1448):
```javascript
xAxis={[{
  label: '', // ラベル非表示
  min: (() => {
    const allValues = resultHistory.flatMap(cycle => 
      cycle.simulationData.map(data => data[selectedXAxis] || 0)
    );
    const minValue = allValues.length > 0 ? Math.min(...allValues) : 0;
    // Ensure minimum value has buffer space
    return Math.min(minValue * 0.9, 0);
  })(),
  max: (() => {
    const allValues = resultHistory.flatMap(cycle => 
      cycle.simulationData.map(data => data[selectedXAxis] || 0)
    );
    const maxValue = allValues.length > 0 ? Math.max(...allValues) : 100;
    // 15% buffer space to prevent data truncation
    return maxValue * 1.15;
  })()
}]}
```

**Y-axis Enhancement** (lines 1449-1467):
```javascript
yAxis={[{
  label: '', // ラベル非表示
  min: (() => {
    const allValues = resultHistory.flatMap(cycle => 
      cycle.simulationData.map(data => data[selectedYAxis] || 0)
    );
    const minValue = allValues.length > 0 ? Math.min(...allValues) : 0;
    // Ensure minimum value has buffer space
    return Math.min(minValue * 0.9, 0);
  })(),
  max: (() => {
    const allValues = resultHistory.flatMap(cycle => 
      cycle.simulationData.map(data => data[selectedYAxis] || 0)
    );
    const maxValue = allValues.length > 0 ? Math.max(...allValues) : 100;
    // 15% buffer space to prevent data truncation
    return maxValue * 1.15;
  })()
}]}
```

**Key Improvements:**
- ✅ **Increased buffer to 15%** for scatter plots
- ✅ **Dynamic minimum calculation** with proper fallback
- ✅ **Consistent behavior** across both axes
- ✅ **Handles edge cases** with empty data

## 🎯 **Benefits of the Fix**

### **1. Adaptive Range**
- Charts now automatically adjust to show all data points
- No more truncated values at the top or bottom
- Maintains visual clarity with appropriate spacing

### **2. Robust Data Handling**
- Handles null/undefined values gracefully
- Works with different data ranges across indicators
- Includes prediction data in range calculations

### **3. User Experience**
- All data is always visible
- Consistent behavior across different chart types
- Maintains readability with appropriate margins

### **4. Backward Compatibility**
- Still respects configuration minimums/maximums as baselines
- Extends range only when necessary
- Preserves existing chart styling and behavior

## 🧪 **Testing Recommendations**

To verify the fix works correctly:

1. **Test with extreme values**: Try scenarios that produce very high or low values
2. **Test different indicators**: Switch between different Y-axis options
3. **Test prediction modes**: Verify with best-worst and monte-carlo predictions
4. **Test scatter plots**: Check both X and Y axis scaling in comparison view
5. **Test edge cases**: Empty data, single data points, negative values

## 📊 **Expected Results**

After this fix:
- ✅ No data points should be cut off or hidden
- ✅ Charts should have appropriate white space around data
- ✅ Y-axis should adapt to actual data range
- ✅ Both line charts and scatter plots should work consistently
- ✅ All visualization modes should display properly

The Y-axis truncation issue should now be completely resolved! 🎉
