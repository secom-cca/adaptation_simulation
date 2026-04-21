// 多语言文本配置

export const texts = {
  ja: {
    title: '気候変動適応策検討シミュレーション',
    cycle: 'サイクル',
    year: '年',
    cropYield: '収穫量',
    floodDamage: '洪水被害',
    ecosystemLevel: '生態系',
    urbanLevel: '都市利便性',
    municipalCost: '予算',
    temperature: '年平均気温',
    precipitation: '年降水量',
    availableWater: '利用可能な水量',
    unit: {
      tonHa: 'ton/ha',
      manYen: '万円',
      none: '-',
      celsius: '℃',
      mm: 'mm'
    },
    mode: {
      group: '（１）グループモード',
      upstream: '（２）上流モード',
      downstream: '（３）下流モード',
      groupDesc: '全ての項目を操作可能',
      upstreamDesc: '植林・河川堤防・田んぼダムのみ',
      downstreamDesc: '田んぼダム・住宅移転・防災訓練のみ'
    },
    predictMode: {
      bestWorst: 'モード（１）：ベストケース・ワーストケース',
      monteCarlo: 'モード（２）：モンテカルロシミュレーション（10回）',
      none: 'モード（３）：予測結果を表示しない'
    },
    settings: {
      title: '設定',
      predictDataMode: '折れ線グラフの予測データ表示モード',
      languageMode: '言語設定',
      close: '閉じる'
    },
    dialog: {
      nameTitle: 'お名前とモードを入力してください',
      nameLabel: 'お名前',
      modeTitle: 'モードを選択してください',
      register: '登録',
      nameError: 'この名前は既に使用されています。別の名前を入力してください。'
    },
    sliders: {
      plantingTrees: '植林・森林保全',
      transportation: '公共バス',
      damLevee: '河川堤防',
      agriculturalRnD: '高温耐性品種',
      houseMigration: '住宅移転',
      paddyDam: '田んぼダム',
      capacityBuilding: '防災訓練・啓発'
    },
    chart: {
      measuredValue: '実測値',
      upperLimit: '上限値予測',
      lowerLimit: '下限値予測',
      monteCarlo: 'モンテカルロ',
      selectYAxis: '縦軸を選択',
      years: 'Years',
      weatherCondition: '年の気象条件と将来影響予測',
      averageTemp: '年平均気温',
      annualPrecip: '年降水量',
      heavyRainFreq: '大雨の頻度',
      residentBurden: '住民の負担',
      biodiversity: '生物多様性',
      frequency: '回/年'
    },
    buttons: {
      advanceYears: '25年進める',
      inputComplete: '回の入力完了',
      nextCycle: '次のサイクル (',
      startNext: ') を開始',
      cycleComplete: 'サイクル',
      completed: 'が完了しました！',
      viewResults: '結果を見る',
      viewModel: 'モデルの説明を見る'
    },
    scatter: {
      title: 'サイクルの比較',
      description: '各サイクルの2050年、2075年、2100年の評価を比較',
      xAxis: 'X軸（横軸）',
      yAxis: 'Y軸（縦軸）',
      markerSize: 'マーカーサイズと透明度（時点）:',
      small: '2050年',
      medium: '2075年',
      large: '2100年',
      cycleColor: 'サイクル色:',
      inputHistory: '各サイクルの入力履歴',
      cycle: 'サイクル',
      inputCount: '入力回数',
      inputYear: '入力年',
      noCompletedCycles: '完了したサイクルがありません。サイクルを完了すると結果が表示されます。'
    }
  },
  en: {
    title: 'Climate Change Adaptation Strategy Simulation',
    cycle: 'Cycle',
    year: 'Year',
    cropYield: 'Crop Yield',
    floodDamage: 'Flood Damage',
    ecosystemLevel: 'Ecosystem Level',
    urbanLevel: 'Urban Level',
    municipalCost: 'Municipal Cost',
    temperature: 'Average Temperature',
    precipitation: 'Annual Precipitation',
    availableWater: 'Available Water',
    unit: {
      tonHa: 'ton/ha',
      manYen: '10k yen',
      none: '-',
      celsius: '°C',
      mm: 'mm'
    },
    mode: {
      group: '(1) Group Mode',
      upstream: '(2) Upstream Mode',
      downstream: '(3) Downstream Mode',
      groupDesc: 'All items can be operated',
      upstreamDesc: 'Forest conservation, river levee, paddy dam only',
      downstreamDesc: 'Paddy dam, house migration, disaster training only'
    },
    predictMode: {
      bestWorst: 'Mode (1): Best Case - Worst Case',
      monteCarlo: 'Mode (2): Monte Carlo Simulation (10 times)',
      none: 'Mode (3): No prediction display'
    },
    settings: {
      title: 'Settings',
      predictDataMode: 'Line Chart Prediction Data Display Mode',
      languageMode: 'Language Settings',
      close: 'Close'
    },
    dialog: {
      nameTitle: 'Enter your name and select mode',
      nameLabel: 'Name',
      modeTitle: 'Please select a mode',
      register: 'Register',
      nameError: 'This name is already in use. Please enter a different name.'
    },
    sliders: {
      plantingTrees: 'Forest Conservation',
      transportation: 'Public Transportation',
      damLevee: 'River Levee',
      agriculturalRnD: 'Heat-resistant Varieties',
      houseMigration: 'House Migration',
      paddyDam: 'Paddy Dam',
      capacityBuilding: 'Disaster Training'
    },
    chart: {
      measuredValue: 'Measured Value',
      upperLimit: 'Upper Limit Prediction',
      lowerLimit: 'Lower Limit Prediction',
      monteCarlo: 'Monte Carlo',
      selectYAxis: 'Select Y-axis',
      years: 'Years',
      weatherCondition: 'Weather Conditions and Future Impact Predictions',
      averageTemp: 'Average Temperature',
      annualPrecip: 'Annual Precipitation',
      heavyRainFreq: 'Heavy Rain Frequency',
      residentBurden: 'Resident Burden',
      biodiversity: 'Biodiversity',
      frequency: 'times/year'
    },
    buttons: {
      advanceYears: '25 years advance',
      inputComplete: 'inputs completed',
      nextCycle: 'Next Cycle (',
      startNext: ') Start',
      cycleComplete: 'Cycle',
      completed: 'completed!',
      viewResults: 'View Results',
      viewModel: 'View Model Description'
    },
    scatter: {
      title: 'Cycle Comparison',
      description: 'Compare evaluations of 2050, 2075, and 2100 for each cycle',
      xAxis: 'X-axis',
      yAxis: 'Y-axis',
      markerSize: 'Marker Size and Opacity (Time Point):',
      small: '2050',
      medium: '2075',
      large: '2100',
      cycleColor: 'Cycle Color:',
      inputHistory: 'Input History for Each Cycle',
      cycle: 'Cycle',
      inputCount: 'Input Count',
      inputYear: 'Input Year',
      noCompletedCycles: 'No completed cycles. Results will be displayed when cycles are completed.'
    }
  }
};
