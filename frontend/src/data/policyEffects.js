const policy = (key, icon, iconFile, labelJa, labelEn, descriptionJa, descriptionEn) => ({
  key,
  icon,
  iconFile,
  label: { ja: labelJa, en: labelEn },
  description: { ja: descriptionJa, en: descriptionEn },
})

const allPolicies = [
  policy(
    'planting_trees_amount',
    'forest',
    'forest.png',
    '植林・森林保全',
    'Forest restoration and conservation',
    '森林を回復し、雨水を一時的にためる力と生きもののすみかを支えます。',
    'Restores forests, increasing water retention and supporting wildlife habitats.',
  ),
  policy(
    'dam_levee_construction_cost',
    'levee',
    'levee.png',
    '堤防・河川改修',
    'Levees and river improvements',
    '堤防や河川改修により、大雨時の越流水を減らします。最低5ポイントから実施できます。',
    'Reduces overflow during heavy rain. Requires a minimum investment of 5 points.',
  ),
  policy(
    'paddy_dam_construction_cost',
    'paddy',
    'paddy.png',
    '田んぼダム',
    'Paddy-field dams',
    '水田に雨水を一時的にため、導入面積に応じて洪水時の流出を抑えます。',
    'Temporarily stores rainwater in rice paddies to reduce flood runoff.',
  ),
  policy(
    'house_migration_amount',
    'relocation',
    'relocation.png',
    '住宅移転',
    'Home relocation',
    '洪水リスクの高い地域に残る住宅を減らします。',
    'Reduces the number of homes remaining in high-flood-risk areas.',
  ),
  policy(
    'capacity_building_cost',
    'preparedness',
    'preparedness.png',
    '防災訓練',
    'Disaster preparedness training',
    '避難訓練や防災訓練で住民の災害対応力を高めます。1ターン最大1ポイントです。',
    'Improves residents’ disaster response skills. Limited to 1 point per turn.',
  ),
  policy(
    'agricultural_RnD_cost',
    'agri-rnd',
    'research.png',
    '農業R&D',
    'Agricultural R&D',
    '高温に強い品種や栽培技術を広げます。1ターン最大2ポイントです。',
    'Develops heat-tolerant crops and farming methods. Limited to 2 points per turn.',
  ),
]

export const POLICIES = {
  upstream: allPolicies.filter(p => ['planting_trees_amount', 'dam_levee_construction_cost', 'paddy_dam_construction_cost'].includes(p.key)),
  downstream: allPolicies.filter(p => ['house_migration_amount', 'capacity_building_cost', 'agricultural_RnD_cost'].includes(p.key)),
  team: allPolicies,
}

const POLICY_EFFECT_EN = {
  '森林が成長すると、雨水を一時的にためる力と生態系のすみかが少しずつ回復します。': 'As the forest grows, its ability to retain rainwater and provide wildlife habitat gradually recovers.',
  '効果が出るまで時間がかかるため、短期の洪水被害には別の対策も必要です。': 'Because these benefits take time to emerge, other measures are also needed to reduce near-term flood damage.',
  '将来の森林面積の回復につながり、流域の保水力を高めます。': 'Helps restore forest cover and increases the basin’s capacity to retain water over time.',
  '生きもののすみかが増え、生態系指標を支えます。': 'Expands wildlife habitat and improves the ecosystem score.',
  '長期的な流域の回復を強く後押しします。': 'Makes a major contribution to the basin’s long-term recovery.',
  '治水対策や被害を軽減するための対策を取る必要があります。': 'Additional flood-control and damage-reduction measures are still needed.',
  '5ポイント未満では事業化されません。': 'The project cannot proceed with an investment of fewer than 5 points.',
  '完成後は大雨時の越流水を減らします。': 'Once completed, it reduces overflow during heavy rain.',
  '20mm刻みで防御水準が上がります。': 'Raises the flood protection level in 20 mm increments.',
  '完成まで時間がかかるため、その間の被害軽減策も必要です。': 'Because construction takes time, interim damage-reduction measures are also needed.',
  '大きな洪水被害を抑えやすくなります。': 'Makes it easier to limit damage from major floods.',
  '自然環境とのバランスに注意が必要です。': 'The impact on the natural environment must also be considered.',
  '水田に雨水をためる取り組みが始まります。': 'Begins the use of rice paddies to temporarily store rainwater.',
  '小規模でも分散型治水の効果があります。': 'Even small-scale adoption contributes to distributed flood management.',
  '導入面積が広がり、洪水時の流出を抑えやすくなります。': 'Expands the area in use, helping reduce runoff during floods.',
  '単独では大規模洪水を止めきれないため、他の治水対策も必要です。': 'Cannot prevent major floods on its own, so other flood-control measures are also needed.',
  '導入上限に近づき、分散型治水の効果が大きくなります。': 'Approaches the maximum adoption area, substantially increasing the benefits of distributed flood management.',
  '導入可能面積に近づくと、追加効果は小さくなります。': 'Additional benefits diminish as the maximum available area is approached.',
  '洪水リスクの高い地域に残る住宅が減ります。': 'Reduces the number of homes remaining in high-flood-risk areas.',
  '移転後のインフラ維持費が将来予算を圧迫する場合があります。': 'The cost of maintaining infrastructure after relocation may put pressure on future budgets.',
  '住宅被害リスクを直接下げやすくなります。': 'Directly reduces the risk of damage to homes.',
  '累積20ポイントが上限です。': 'Total investment is capped at 20 points.',
  '高リスク地域の住宅被害リスクを大きく下げます。': 'Greatly reduces the risk of damage to homes in high-risk areas.',
  '移転可能な住宅が少なくなると追加効果は小さくなります。': 'Additional benefits diminish as fewer homes remain eligible for relocation.',
  '洪水時にどう行動すればよいかを学ぶ取り組みです。': 'Helps residents learn how to respond during a flood.',
  '1ターン最大1ポイントです。': 'Investment is limited to 1 point per turn.',
  '継続すると住民の災害対応力が高まります。': 'Continued training strengthens community disaster preparedness.',
  '洪水そのものを止める政策ではありません。': 'Does not prevent flooding itself.',
  '初動対応が改善し、被害軽減につながります。': 'Improves the initial response and helps reduce damage.',
  'このターンはこれ以上増やせません。': 'No further investment can be made this turn.',
  '高温に強い品種や栽培技術の開発が進みます。': 'Advances the development of heat-tolerant crops and farming methods.',
  '洪水被害は直接減らしません。': 'Does not directly reduce flood damage.',
  '高温による品質低下や収量低下を抑えやすくなります。': 'Helps limit heat-related declines in crop quality and yield.',
  '研究と普及には時間がかかります。': 'Research and widespread adoption take time.',
  '温暖化への追随力が高まります。': 'Strengthens agriculture’s ability to adapt to rising temperatures.',
  '1ターン最大2ポイントです。': 'Investment is limited to 2 points per turn.',
}

// ここを編集すると、政策スライダー下の「プラス面 / マイナス面」の文章を変更できます。
export const POLICY_EFFECT_DRAFT_TEXTS = {
  planting_trees_amount: {
    weak: [
      { positive: true, text: '森林が成長すると、雨水を一時的にためる力と生態系のすみかが少しずつ回復します。' },
      { positive: false, text: '効果が出るまで時間がかかるため、短期の洪水被害には別の対策も必要です。' },
    ],
    standard: [
      { positive: true, text: '将来の森林面積の回復につながり、流域の保水力を高めます。' },
      { positive: true, text: '生きもののすみかが増え、生態系指標を支えます。' },
    ],
    strong: [
      { positive: true, text: '長期的な流域の回復を強く後押しします。' },
      { positive: false, text: '治水対策や被害を軽減するための対策を取る必要があります。' },
    ],
  },
  dam_levee_construction_cost: {
    weak: [
      { positive: false, text: '5ポイント未満では事業化されません。' },
      { positive: true, text: '完成後は大雨時の越流水を減らします。' },
    ],
    standard: [
      { positive: true, text: '20mm刻みで防御水準が上がります。' },
      { positive: false, text: '完成まで時間がかかるため、その間の被害軽減策も必要です。' },
    ],
    strong: [
      { positive: true, text: '大きな洪水被害を抑えやすくなります。' },
      { positive: false, text: '自然環境とのバランスに注意が必要です。' },
    ],
  },
  paddy_dam_construction_cost: {
    weak: [
      { positive: true, text: '水田に雨水をためる取り組みが始まります。' },
      { positive: true, text: '小規模でも分散型治水の効果があります。' },
    ],
    standard: [
      { positive: true, text: '導入面積が広がり、洪水時の流出を抑えやすくなります。' },
      { positive: false, text: '単独では大規模洪水を止めきれないため、他の治水対策も必要です。' },
    ],
    strong: [
      { positive: true, text: '導入上限に近づき、分散型治水の効果が大きくなります。' },
      { positive: false, text: '導入可能面積に近づくと、追加効果は小さくなります。' },
    ],
  },
  house_migration_amount: {
    weak: [
      { positive: true, text: '洪水リスクの高い地域に残る住宅が減ります。' },
      { positive: false, text: '移転後のインフラ維持費が将来予算を圧迫する場合があります。' },
    ],
    standard: [
      { positive: true, text: '住宅被害リスクを直接下げやすくなります。' },
      { positive: false, text: '累積20ポイントが上限です。' },
    ],
    strong: [
      { positive: true, text: '高リスク地域の住宅被害リスクを大きく下げます。' },
      { positive: false, text: '移転可能な住宅が少なくなると追加効果は小さくなります。' },
    ],
  },
  capacity_building_cost: {
    weak: [
      { positive: true, text: '洪水時にどう行動すればよいかを学ぶ取り組みです。' },
      { positive: false, text: '1ターン最大1ポイントです。' },
    ],
    standard: [
      { positive: true, text: '継続すると住民の災害対応力が高まります。' },
      { positive: false, text: '洪水そのものを止める政策ではありません。' },
    ],
    strong: [
      { positive: true, text: '初動対応が改善し、被害軽減につながります。' },
      { positive: false, text: 'このターンはこれ以上増やせません。' },
    ],
  },
  agricultural_RnD_cost: {
    weak: [
      { positive: true, text: '高温に強い品種や栽培技術の開発が進みます。' },
      { positive: false, text: '洪水被害は直接減らしません。' },
    ],
    standard: [
      { positive: true, text: '高温による品質低下や収量低下を抑えやすくなります。' },
      { positive: false, text: '研究と普及には時間がかかります。' },
    ],
    strong: [
      { positive: true, text: '温暖化への追随力が高まります。' },
      { positive: false, text: '1ターン最大2ポイントです。' },
    ],
  },
}

export const POLICY_EFFECTS = Object.fromEntries(
  Object.entries(POLICY_EFFECT_DRAFT_TEXTS).map(([key, tiers]) => [
    key,
    Object.fromEntries(
      Object.entries(tiers).map(([tier, items]) => [
        tier,
        items.map(item => ({ ...item, text: { ja: item.text, en: POLICY_EFFECT_EN[item.text] } })),
      ]),
    ),
  ]),
)

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
