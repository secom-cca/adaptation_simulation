// 应用常量配置

// 仿真相关常量
export const SIMULATION_YEARS = 25; // 一回のシミュレーションで進める年数を決定する 
export const LINE_CHART_DISPLAY_INTERVAL = 100; // ms

// 指标转换配置
export const INDICATOR_CONVERSION = {
  'Municipal Cost': 1 / 10000, // 円 → 億円
  'Flood Damage': 1 / 10000, // 円 → 万円
  'Crop Yield': 1 / 1000 // kg → ton（例）
};

// 图表指标配置
export const getLineChartIndicators = (language) => {
  const indicators = {
    ja: {
      'Crop Yield': { labelTitle: '収穫量', max: 5, min: 0, unit: 'ton/ha' },
      'Flood Damage': { labelTitle: '洪水被害', max: 10000, min: 0, unit: '万円' },
      'Ecosystem Level': { labelTitle: '生態系', max: 100, min: 0, unit: '-' },
      'Urban Level': { labelTitle: '都市利便性', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: '予算', max: 100000, min: 0, unit: '万円' },
      'Temperature (℃)': { labelTitle: '年平均気温', max: 18, min: 12, unit: '℃' },
      'Precipitation (mm)': { labelTitle: '年降水量', max: 3000, min: 0, unit: 'mm' },
      'Available Water': { labelTitle: '利用可能な水量', max: 3000, min: 0, unit: 'mm' }
    },
    en: {
      'Crop Yield': { labelTitle: 'Crop Yield', max: 5, min: 0, unit: 'ton/ha' },
      'Flood Damage': { labelTitle: 'Flood Damage', max: 10000, min: 0, unit: '10k yen' },
      'Ecosystem Level': { labelTitle: 'Ecosystem Level', max: 100, min: 0, unit: '-' },
      'Urban Level': { labelTitle: 'Urban Level', max: 100, min: 0, unit: '-' },
      'Municipal Cost': { labelTitle: 'Municipal Cost', max: 100000, min: 0, unit: '10k yen' },
      'Temperature (℃)': { labelTitle: 'Average Temperature', max: 18, min: 12, unit: '°C' },
      'Precipitation (mm)': { labelTitle: 'Annual Precipitation', max: 3000, min: 0, unit: 'mm' },
      'Available Water': { labelTitle: 'Available Water', max: 3000, min: 0, unit: 'mm' }
    }
  };
  return indicators[language] || indicators.ja;
};
