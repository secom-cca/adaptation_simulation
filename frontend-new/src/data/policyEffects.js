// Static projected outcome descriptions per policy × tier
// tier: 'weak' (1-3), 'standard' (4-7), 'strong' (8-10)

export const POLICIES = {
  upstream: [
    {
      key: 'planting_trees_amount',
      label: { en: 'Forest Planting', ja: '植林・森林保全' },
      description: { en: 'Reforestation for watershed protection', ja: '流域保護のための植林' },
      icon: '🌲',
    },
    {
      key: 'dam_levee_construction_cost',
      label: { en: 'Levee / Flood Protection', ja: '堤防・洪水対策' },
      description: { en: 'Infrastructure investment for flood defense', ja: '洪水防御のためのインフラ投資' },
      icon: '🛡',
    },
    {
      key: 'paddy_dam_construction_cost',
      label: { en: 'Paddy Dam', ja: '田んぼダム' },
      description: { en: 'Agricultural water retention infrastructure', ja: '農業用水保持インフラ' },
      icon: '🌾',
    },
  ],
  downstream: [
    {
      key: 'dam_levee_construction_cost',
      label: { en: 'Levee / Flood Protection', ja: '堤防・洪水対策' },
      description: { en: 'Infrastructure investment for flood defense', ja: '洪水防御のためのインフラ投資' },
      icon: '🛡',
    },
    {
      key: 'house_migration_amount',
      label: { en: 'Relocation / Adaptation', ja: '移住・適応支援' },
      description: { en: 'Resident relocation and community resilience', ja: '居住者移転とコミュニティ強靭化' },
      icon: '🏘',
    },
    {
      key: 'capacity_building_cost',
      label: { en: 'Disaster Training', ja: '防災能力構築' },
      description: { en: 'Community disaster preparedness programs', ja: '地域防災プログラム' },
      icon: '📋',
    },
  ],
  team: [
    {
      key: 'planting_trees_amount',
      label: { en: 'Forest Planting', ja: '植林・森林保全' },
      description: { en: 'Reforestation for watershed protection', ja: '流域保護のための植林' },
      icon: '🌲',
    },
    {
      key: 'dam_levee_construction_cost',
      label: { en: 'Levee / Flood Protection', ja: '堤防・洪水対策' },
      description: { en: 'Infrastructure investment for flood defense', ja: '洪水防御のためのインフラ投資' },
      icon: '🛡',
    },
    {
      key: 'paddy_dam_construction_cost',
      label: { en: 'Paddy Dam', ja: '田んぼダム' },
      description: { en: 'Agricultural water retention infrastructure', ja: '農業用水保持インフラ' },
      icon: '🌾',
    },
    {
      key: 'house_migration_amount',
      label: { en: 'Relocation', ja: '移住・適応支援' },
      description: { en: 'Resident relocation and community resilience', ja: '居住者移転と強靭化' },
      icon: '🏘',
    },
    {
      key: 'capacity_building_cost',
      label: { en: 'Disaster Training', ja: '防災能力構築' },
      description: { en: 'Community disaster preparedness', ja: '地域防災プログラム' },
      icon: '📋',
    },
    {
      key: 'agricultural_RnD_cost',
      label: { en: 'Agricultural R&D', ja: '農業技術研究' },
      description: { en: 'Heat-resilient farming and crop innovation', ja: '耐熱農業・作物イノベーション' },
      icon: '🔬',
    },
  ],
}

export const POLICY_EFFECTS = {
  planting_trees_amount: {
    weak: [
      { positive: false, text: { en: 'Minimal forest coverage gain', ja: '森林面積の増加はわずか' } },
      { positive: true,  text: { en: 'Negligible budget impact', ja: '予算への影響はほぼなし' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Moderate runoff reduction over time', ja: '中期的に流出量が低下' } },
      { positive: true,  text: { en: 'Improved ecosystem level', ja: '生態系レベルが改善' } },
      { positive: false, text: { en: 'Long maturation period (30 yr)', ja: '効果発現に30年かかる' } },
    ],
    strong: [
      { positive: true,  text: { en: 'Significant flood buffering by 2075+', ja: '2075年以降に大きな洪水緩衝効果' } },
      { positive: true,  text: { en: 'Substantial biodiversity recovery', ja: '生物多様性が大幅に回復' } },
      { positive: false, text: { en: 'High upfront planting cost', ja: '初期植林コストが高い' } },
    ],
  },
  dam_levee_construction_cost: {
    weak: [
      { positive: false, text: { en: 'Minimal flood protection improvement', ja: '洪水防御の改善はわずか' } },
      { positive: true,  text: { en: 'Low fiscal burden', ja: '財政負担は低い' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Reduced flood damage by ~30%', ja: '洪水被害が約30%減少' } },
      { positive: false, text: { en: 'Moderate fiscal burden increase', ja: '財政負担が中程度増加' } },
      { positive: true,  text: { en: 'Lower resident stress downstream', ja: '下流域の住民ストレスが低下' } },
    ],
    strong: [
      { positive: true,  text: { en: 'Major flood risk reduction', ja: '洪水リスクが大幅に低下' } },
      { positive: false, text: { en: 'High infrastructure investment', ja: 'インフラ投資コストが高い' } },
      { positive: true,  text: { en: 'Long-term community resilience', ja: '長期的なコミュニティ強靭性' } },
    ],
  },
  paddy_dam_construction_cost: {
    weak: [
      { positive: false, text: { en: 'Negligible water retention effect', ja: '水保持効果はほぼなし' } },
      { positive: true,  text: { en: 'Minimal cost', ja: 'コストは最小限' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Moderate peak flow reduction', ja: 'ピーク流量が中程度減少' } },
      { positive: true,  text: { en: 'Some improvement to crop water access', ja: '農業用水へのアクセスが改善' } },
      { positive: false, text: { en: 'Requires paddy field cooperation', ja: '水田の協力が必要' } },
    ],
    strong: [
      { positive: true,  text: { en: 'Significant downstream flood mitigation', ja: '下流の洪水緩和に大きな効果' } },
      { positive: true,  text: { en: 'Improved agricultural resilience', ja: '農業の強靭性が向上' } },
      { positive: false, text: { en: 'High coordination and construction cost', ja: '調整・建設コストが高い' } },
    ],
  },
  house_migration_amount: {
    weak: [
      { positive: false, text: { en: 'Most high-risk households remain', ja: '危険な住宅のほとんどが残る' } },
      { positive: true,  text: { en: 'Low disruption to community', ja: 'コミュニティへの混乱は少ない' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Moderate reduction in flood exposure', ja: '洪水リスクへの曝露が中程度低下' } },
      { positive: false, text: { en: 'Resident burden temporarily elevated', ja: '一時的に住民負担が増加' } },
      { positive: true,  text: { en: 'Long-term safety improvement', ja: '長期的な安全性が向上' } },
    ],
    strong: [
      { positive: true,  text: { en: 'Substantial relocation from flood zones', ja: '洪水危険区域からの大規模移転' } },
      { positive: false, text: { en: 'High per-household relocation cost', ja: '1世帯あたりの移転費用が高い' } },
      { positive: true,  text: { en: 'Greatly reduced disaster casualties', ja: '災害による被害が大幅に減少' } },
    ],
  },
  capacity_building_cost: {
    weak: [
      { positive: false, text: { en: 'Minimal preparedness improvement', ja: '防災力の改善はわずか' } },
      { positive: true,  text: { en: 'Very low cost', ja: 'コストは非常に低い' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Improved community risk awareness', ja: 'コミュニティのリスク意識が向上' } },
      { positive: true,  text: { en: 'Faster disaster response', ja: '災害対応が迅速化' } },
      { positive: false, text: { en: 'Ongoing training cost', ja: '継続的な訓練コストが発生' } },
    ],
    strong: [
      { positive: true,  text: { en: 'High community resilience capacity', ja: 'コミュニティの強靭性が大幅向上' } },
      { positive: true,  text: { en: 'Reduced long-term disaster losses', ja: '長期的な災害損失が低下' } },
      { positive: false, text: { en: 'Significant sustained investment needed', ja: '持続的な大規模投資が必要' } },
    ],
  },
  agricultural_RnD_cost: {
    weak: [
      { positive: false, text: { en: 'No threshold reached — no effect', ja: '閾値未達のため効果なし' } },
      { positive: true,  text: { en: 'Low fiscal impact', ja: '財政への影響は低い' } },
    ],
    standard: [
      { positive: true,  text: { en: 'Heat-tolerant crop varieties developed', ja: '耐熱性作物品種が開発される' } },
      { positive: true,  text: { en: 'Crop yield stabilization over time', ja: '収穫量が中期的に安定化' } },
      { positive: false, text: { en: 'Minimum 5-year investment required', ja: '最低5年間の投資が必要' } },
    ],
    strong: [
      { positive: true,  text: { en: 'Significant yield recovery under heat stress', ja: '高温ストレス下でも大幅な収穫回復' } },
      { positive: true,  text: { en: 'Long-term food security improvement', ja: '長期的な食料安全保障の向上' } },
      { positive: false, text: { en: 'High R&D investment with delayed return', ja: 'R&D投資は高く、効果発現が遅い' } },
    ],
  },
}

export function getTier(value) {
  if (value < 3) return 'weak'
  if (value < 8) return 'standard'
  return 'strong'
}

// Map policy points 0-10 to backend parameter values.
export const POLICY_SCALE = {
  planting_trees_amount:       { min: 0,   max: 100  },
  dam_levee_construction_cost: { min: 0,   max: 10   },
  paddy_dam_construction_cost: { min: 0,   max: 10   },
  house_migration_amount:      { min: 0,   max: 500  },
  capacity_building_cost:      { min: 0,   max: 5    },
  agricultural_RnD_cost:       { min: 0,   max: 5    },
  transportation_invest:       { min: 0,   max: 5    },
}

export function sliderToBackend(policyKey, sliderValue) {
  const { min, max } = POLICY_SCALE[policyKey]
  const points = Math.max(0, Math.min(10, Number(sliderValue) || 0))
  return min + (points / 10) * (max - min)
}
