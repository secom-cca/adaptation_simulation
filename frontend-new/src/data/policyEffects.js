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
    'Forest restoration',
    '森林を回復し、雨水を一時的にためる力と生きもののすみかを支えます。',
    'Restores forest retention and habitat.',
  ),
  policy(
    'dam_levee_construction_cost',
    'levee',
    'levee.png',
    '堤防・河川改修',
    'Levee / river works',
    '堤防や河川改修により、大雨時の越流水を減らします。最低5ポイントから実施できます。',
    'Large flood-control works; minimum 5 points.',
  ),
  policy(
    'paddy_dam_construction_cost',
    'paddy',
    'paddy.png',
    '田んぼダム',
    'Paddy dam',
    '水田に雨水を一時的にため、導入面積に応じて洪水時の流出を抑えます。',
    'Stores runoff temporarily in paddy fields.',
  ),
  policy(
    'house_migration_amount',
    'relocation',
    'relocation.png',
    '住宅移転',
    'Relocation support',
    '洪水リスクの高い地域に残る住宅を減らします。',
    'Moves exposed homes to safer areas.',
  ),
  policy(
    'capacity_building_cost',
    'preparedness',
    'preparedness.png',
    '防災訓練',
    'Disaster preparedness',
    '避難訓練や防災訓練で住民の災害対応力を高めます。1ターン最大1ポイントです。',
    'Improves preparedness; turn cap 1 point.',
  ),
  policy(
    'agricultural_RnD_cost',
    'agri-rnd',
    'research.png',
    '農業R&D',
    'Agricultural R&D',
    '高温に強い品種や栽培技術を広げます。1ターン最大2ポイントです。',
    'Improves heat tolerance; turn cap 2 points.',
  ),
]

export const POLICIES = {
  upstream: allPolicies.filter(p => ['planting_trees_amount', 'dam_levee_construction_cost', 'paddy_dam_construction_cost'].includes(p.key)),
  downstream: allPolicies.filter(p => ['house_migration_amount', 'capacity_building_cost', 'agricultural_RnD_cost'].includes(p.key)),
  team: allPolicies,
}

const ja = text => ({ ja: text, en: text })

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
        items.map(item => ({ ...item, text: ja(item.text) })),
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
