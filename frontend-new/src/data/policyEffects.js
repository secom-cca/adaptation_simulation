export const POLICIES = {
  upstream: [
    {
      key: 'planting_trees_amount',
      icon: '🌲',
      label: { ja: '植林・森林保全', en: 'Forest restoration' },
      description: { ja: '流域の保水力を高める長期対策', en: 'Long-term watershed retention' },
    },
    {
      key: 'dam_levee_construction_cost',
      icon: '🛡️',
      label: { ja: '堤防・洪水対策', en: 'Levee / river works' },
      description: { ja: '大雨の越流水を直接減らす大型事業', en: 'Large works that directly reduce overflow' },
    },
    {
      key: 'paddy_dam_construction_cost',
      icon: '🌾',
      label: { ja: '田んぼダム', en: 'Paddy dam' },
      description: { ja: '水田で雨水を一時的に受け止める', en: 'Stores runoff temporarily in paddy fields' },
    },
  ],
  downstream: [
    {
      key: 'house_migration_amount',
      icon: '🏘️',
      label: { ja: '移住・適応支援', en: 'Relocation support' },
      description: { ja: '浸水リスクの高い住宅を安全側へ移す', en: 'Moves exposed homes to safer areas' },
    },
    {
      key: 'capacity_building_cost',
      icon: '📋',
      label: { ja: '防災能力構築', en: 'Disaster preparedness' },
      description: { ja: '避難訓練と地域防災プログラム', en: 'Evacuation drills and local preparedness' },
    },
    {
      key: 'agricultural_RnD_cost',
      icon: '🔬',
      label: { ja: '農業技術研究', en: 'Agricultural adaptation R&D' },
      description: { ja: '高温耐性品種と栽培技術の普及', en: 'Heat-tolerant crops and farming methods' },
    },
  ],
  team: [
    {
      key: 'planting_trees_amount',
      icon: '🌲',
      label: { ja: '植林・森林保全', en: 'Forest restoration' },
      description: { ja: '長期的に洪水・生態系を改善', en: 'Improves floods and ecosystems over time' },
    },
    {
      key: 'dam_levee_construction_cost',
      icon: '🛡️',
      label: { ja: '堤防・洪水対策', en: 'Levee / river works' },
      description: { ja: '最低5マナからの大型洪水対策', en: 'Large flood project, minimum 5 mana' },
    },
    {
      key: 'paddy_dam_construction_cost',
      icon: '🌾',
      label: { ja: '田んぼダム', en: 'Paddy dam' },
      description: { ja: '小さく積み上げる流域治水', en: 'Distributed flood mitigation' },
    },
    {
      key: 'house_migration_amount',
      icon: '🏘️',
      label: { ja: '移住・適応支援', en: 'Relocation support' },
      description: { ja: '被害を減らすが将来負担も生む', en: 'Cuts losses but raises future costs' },
    },
    {
      key: 'capacity_building_cost',
      icon: '📋',
      label: { ja: '防災能力構築', en: 'Disaster preparedness' },
      description: { ja: '上限1マナの継続訓練', en: 'Turn cap 1 mana' },
    },
    {
      key: 'agricultural_RnD_cost',
      icon: '🔬',
      label: { ja: '農業技術研究', en: 'Agricultural adaptation R&D' },
      description: { ja: '上限2マナの高温適応', en: 'Turn cap 2 mana' },
    },
  ],
}

const ja = text => ({ ja: text, en: text })

export const POLICY_EFFECTS = {
  planting_trees_amount: {
    weak: [
      { positive: true, text: ja('生態系を改善し、森林の保水力が少しずつ高まる') },
      { positive: false, text: ja('効果発現には時間遅れがあり、直後の洪水被害は大きく変わりにくい') },
      { positive: true, text: ja('予算への追加ペナルティはほぼない') },
    ],
    standard: [
      { positive: true, text: ja('数十年後に流出ピークを抑え、洪水被害を下げ始める') },
      { positive: true, text: ja('生態系指標にプラス') },
      { positive: false, text: ja('短期の避難・浸水対策は別途必要') },
    ],
    strong: [
      { positive: true, text: ja('長期的な洪水・生態系の両方に効く') },
      { positive: false, text: ja('1ターン内の即効性は堤防や田んぼダムより弱い') },
      { positive: true, text: ja('将来予算への直接圧迫は小さい') },
    ],
  },
  dam_levee_construction_cost: {
    weak: [
      { positive: false, text: ja('5マナ未満では事業化しない') },
      { positive: true, text: ja('完成後は180mm級豪雨の越流水を段階的に削減') },
      { positive: false, text: ja('大型工事のため生態系への負荷がある') },
    ],
    standard: [
      { positive: true, text: ja('20mm強化ごとに180mm級豪雨の被害を約25%削減') },
      { positive: false, text: ja('完成まで時間遅れがある') },
      { positive: false, text: ja('予算負担が大きく、生態系にはマイナス') },
    ],
    strong: [
      { positive: true, text: ja('大規模洪水の被害を大きく下げる') },
      { positive: false, text: ja('ほかの政策に使えるマナを圧迫しやすい') },
      { positive: false, text: ja('自然環境とのトレードオフが大きい') },
    ],
  },
  paddy_dam_construction_cost: {
    weak: [
      { positive: true, text: ja('小さな投資で下流ピークを少し下げる') },
      { positive: true, text: ja('生態系への悪影響は小さい') },
      { positive: false, text: ja('単独では大規模洪水を止めきれない') },
    ],
    standard: [
      { positive: true, text: ja('累計3マナで180mm級豪雨の越流水を約6%削減') },
      { positive: false, text: ja('農業収量に最大1%程度の小さな負担') },
      { positive: true, text: ja('分散型で即効性がある') },
    ],
    strong: [
      { positive: true, text: ja('累計6マナで最大効果、180mm級豪雨の越流水を約13%削減') },
      { positive: true, text: ja('堤防より生態系負荷が小さい') },
      { positive: false, text: ja('累計上限に達すると追加効果は増えない') },
    ],
  },
  house_migration_amount: {
    weak: [
      { positive: true, text: ja('高リスク住宅の浸水被害を直接減らす') },
      { positive: false, text: ja('累計1マナ超から将来インフラ費用が発生') },
      { positive: false, text: ja('地域コミュニティへの負担がある') },
    ],
    standard: [
      { positive: true, text: ja('大規模洪水時の住宅被害を大きく削減') },
      { positive: false, text: ja('公共交通・道路・上下水道維持費が将来予算を圧迫') },
      { positive: false, text: ja('累計20マナが上限') },
    ],
    strong: [
      { positive: true, text: ja('リスク曝露を根本的に下げる') },
      { positive: false, text: ja('将来の使えるマナが大きく減る可能性') },
      { positive: false, text: ja('生活再建支援と合意形成が重い') },
    ],
  },
  capacity_building_cost: {
    weak: [
      { positive: true, text: ja('住民の避難判断と初動対応を高める') },
      { positive: false, text: ja('上限1マナ。大量投入しても線形には伸びない') },
      { positive: false, text: ja('訓練効果は継続しないと薄れる') },
    ],
    standard: [
      { positive: true, text: ja('小〜中規模洪水で人的・生活被害を抑えやすい') },
      { positive: false, text: ja('堤防のように浸水そのものを止める政策ではない') },
      { positive: false, text: ja('1ターン上限1マナ') },
    ],
    strong: [
      { positive: true, text: ja('地域の防災意識係数が高い水準に近づく') },
      { positive: false, text: ja('上限1マナのため、このターンはこれ以上増やせない') },
      { positive: true, text: ja('低コストで予算負担が小さい') },
    ],
  },
  agricultural_RnD_cost: {
    weak: [
      { positive: true, text: ja('高温耐性品種・栽培技術で食糧生産を守る') },
      { positive: false, text: ja('洪水被害は直接減らさない') },
      { positive: false, text: ja('成果発現には累積投資の時間遅れがある') },
    ],
    standard: [
      { positive: true, text: ja('1マナで25年間に高温耐性が約0.4度向上') },
      { positive: false, text: ja('上限2マナ。研究・普及には速度制約がある') },
      { positive: true, text: ja('作物生産低下イベントを抑えやすい') },
    ],
    strong: [
      { positive: true, text: ja('最大2マナで温暖化ペースにかなり追随') },
      { positive: false, text: ja('このターンは上限2マナまで') },
      { positive: false, text: ja('治水対策とは別に必要') },
    ],
  },
}

export function getTier(value) {
  const v = Number(value) || 0
  if (v <= 0) return 'weak'
  if (v <= 2) return 'weak'
  if (v <= 5) return 'standard'
  return 'strong'
}

export function sliderToBackend(_policyKey, sliderValue) {
  return Math.max(0, Math.min(10, Math.round(Number(sliderValue) || 0)))
}
