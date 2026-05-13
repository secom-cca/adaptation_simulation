export const MANA_JPY_PER_YEAR = 20_000_000
export const TURN_YEARS = 25
export const BASE_POLICY_BUDGET_MANA = 10
export const MIN_POLICY_BUDGET_MANA = 0
export const FLOOD_RECOVERY_COST_COEF = 1.0
export const INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR = 10_000
export const COST_PER_MIGRATION = 975_000
export const MIGRATION_INFRA_PENALTY_START_MANA = 1
export const POLICY_POINT_MAX = 10
export const LEGACY_USD_TO_JPY = 150

export const POPULATION_BUDGET_MULTIPLIER_BY_YEAR = {
  2026: 1.00,
  2050: 0.85,
  2075: 0.68,
  2100: 0.52,
}

export const POLICY_POINT_KEYS = [
  'planting_trees_amount',
  'house_migration_amount',
  'dam_levee_construction_cost',
  'paddy_dam_construction_cost',
  'agricultural_RnD_cost',
  'capacity_building_cost',
]

export const POLICY_MANA_RULES = {
  planting_trees_amount: {
    labelJa: '植林・森林保全',
    labelEn: 'Forest restoration',
    min: 1,
    maxPerTurn: null,
    cumulativeCap: null,
    summaryJa: '時間差で保水力と生態系を改善。洪水被害はゆっくり下がる',
    summaryEn: 'Delayed watershed and ecosystem gains; flood reduction is gradual',
  },
  house_migration_amount: {
    labelJa: '移住・適応支援',
    labelEn: 'Relocation support',
    min: 1,
    maxPerTurn: null,
    cumulativeCap: 20,
    summaryJa: '浸水リスクを直接減らす。累計1マナ超から将来インフラ負担が発生',
    summaryEn: 'Directly lowers exposure; infra penalty starts after 1 cumulative mana',
  },
  dam_levee_construction_cost: {
    labelJa: '堤防・洪水対策',
    labelEn: 'Levee / river works',
    min: 5,
    maxPerTurn: null,
    cumulativeCap: null,
    summaryJa: '最低5マナで事業化。20mm強化で180mm豪雨被害を約25%削減',
    summaryEn: 'Minimum 5 mana; +20mm cuts 180mm-rain overflow by about 25%',
  },
  paddy_dam_construction_cost: {
    labelJa: '田んぼダム',
    labelEn: 'Paddy dam',
    min: 1,
    maxPerTurn: null,
    cumulativeCap: 6,
    summaryJa: '累計6マナで最大。180mm豪雨の越流水を最大約13%削減',
    summaryEn: 'Capped at 6 cumulative mana; cuts 180mm-rain overflow by up to about 13%',
  },
  agricultural_RnD_cost: {
    labelJa: '農業技術研究',
    labelEn: 'Agricultural adaptation R&D',
    min: 1,
    maxPerTurn: 2,
    cumulativeCap: null,
    summaryJa: '上限2マナ。温暖化に追随するが、一気に解決はできない',
    summaryEn: 'Turn cap 2 mana; follows warming over time, not instant',
  },
  capacity_building_cost: {
    labelJa: '防災能力構築',
    labelEn: 'Disaster preparedness',
    min: 1,
    maxPerTurn: 1,
    cumulativeCap: null,
    summaryJa: '上限1マナ。住民対応力を高める継続訓練',
    summaryEn: 'Turn cap 1 mana; sustained training improves resident capacity',
  },
}

export function normalizePolicyPoints(value) {
  return Math.max(0, Math.min(POLICY_POINT_MAX, Math.round(Number(value) || 0)))
}

export function normalizePolicyMana(key, value, policyHistory = [], sliders = {}) {
  const rule = POLICY_MANA_RULES[key] ?? {}
  let mana = normalizePolicyPoints(value)
  if (mana > 0 && rule.min != null && mana < rule.min) mana = 0
  if (rule.maxPerTurn != null) mana = Math.min(mana, rule.maxPerTurn)
  if (rule.cumulativeCap != null) {
    const used = getCumulativePolicyMana(policyHistory, key)
    const current = normalizePolicyPoints(sliders[key])
    mana = Math.min(mana, Math.max(0, rule.cumulativeCap - used + current))
  }
  return mana
}

export function getUsedPolicyPoints(sliders = {}) {
  return POLICY_POINT_KEYS.reduce((sum, key) => sum + normalizePolicyPoints(sliders[key]), 0)
}

export function interpolatePopulationMultiplier(year) {
  const points = Object.entries(POPULATION_BUDGET_MULTIPLIER_BY_YEAR)
    .map(([y, v]) => [Number(y), Number(v)])
    .sort((a, b) => a[0] - b[0])
  if (year <= points[0][0]) return points[0][1]
  if (year >= points[points.length - 1][0]) return points[points.length - 1][1]
  for (let i = 0; i < points.length - 1; i += 1) {
    const [y0, v0] = points[i]
    const [y1, v1] = points[i + 1]
    if (year >= y0 && year <= y1) {
      return Math.min(1, v0 + (v1 - v0) * ((year - y0) / (y1 - y0)))
    }
  }
  return 1
}

export function getFloodDamageJpy(row = {}) {
  const direct = Number(row['Flood Damage JPY'])
  if (Number.isFinite(direct)) return Math.max(0, direct)
  return Math.max(0, Number(row['Flood Damage']) || 0) * LEGACY_USD_TO_JPY
}

export function getFloodDamageForPeriod(rows = [], periodIndex) {
  if (periodIndex < 0) return 0
  const start = periodIndex * TURN_YEARS
  const end = start + TURN_YEARS
  return rows.slice(start, end).reduce((sum, row) => sum + getFloodDamageJpy(row), 0)
}

export function getAverageFloodDamageForLastPeriod(rows = []) {
  const lastRows = rows.slice(-TURN_YEARS)
  if (!lastRows.length) return 0
  return lastRows.reduce((sum, row) => sum + getFloodDamageJpy(row), 0) / lastRows.length
}

export function getCumulativePolicyMana(policyHistory = [], key) {
  return policyHistory.reduce((sum, entry) => sum + normalizePolicyPoints(entry?.sliders?.[key]), 0)
}

export function getCumulativePolicyStats(policyHistory = []) {
  return POLICY_POINT_KEYS.map(key => {
    const rule = POLICY_MANA_RULES[key] ?? {}
    const used = getCumulativePolicyMana(policyHistory, key)
    return {
      key,
      used,
      cap: rule.cumulativeCap,
      remaining: rule.cumulativeCap == null ? null : Math.max(0, rule.cumulativeCap - used),
      labelJa: rule.labelJa,
      labelEn: rule.labelEn,
    }
  })
}

export function buildBudgetRows(policyHistory = [], simulationRows = [], pendingInput = null) {
  const completedEntries = Array.isArray(policyHistory) ? policyHistory : []
  const allEntries = pendingInput ? [...completedEntries, pendingInput] : completedEntries

  return allEntries.map((entry, index) => {
    const sliders = entry?.sliders ?? {}
    const year = entry?.year
    const usedPolicyPoints = getUsedPolicyPoints(sliders)
    const populationMultiplier = interpolatePopulationMultiplier(year ?? 2026)
    const populationPenaltyMana = BASE_POLICY_BUDGET_MANA * Math.max(0, 1 - populationMultiplier)
    const appliedFloodDamage = index === 0 ? 0 : getFloodDamageForPeriod(simulationRows, index - 1) / TURN_YEARS
    const floodPenaltyMana = appliedFloodDamage * FLOOD_RECOVERY_COST_COEF / MANA_JPY_PER_YEAR
    const cumulativeMigrationMana = getCumulativePolicyMana(allEntries.slice(0, index), 'house_migration_amount')
    const chargeableMigrationMana = Math.max(0, cumulativeMigrationMana - MIGRATION_INFRA_PENALTY_START_MANA)
    const housesPerMana = MANA_JPY_PER_YEAR * TURN_YEARS / COST_PER_MIGRATION
    const migrationPenaltyMana = chargeableMigrationMana * housesPerMana * INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR / MANA_JPY_PER_YEAR
    const totalBudgetReduction = populationPenaltyMana + floodPenaltyMana + migrationPenaltyMana
    const availableBudgetPoints = Math.max(MIN_POLICY_BUDGET_MANA, BASE_POLICY_BUDGET_MANA - totalBudgetReduction)
    const periodLabel = `${year ?? '-'} - ${Number.isFinite(year) ? year + 24 : '-'}`

    return {
      year,
      periodLabel,
      sliders,
      appliedFloodDamage,
      populationMultiplier,
      populationPenaltyMana,
      floodReduction: floodPenaltyMana,
      migrationReduction: migrationPenaltyMana,
      totalBudgetReduction,
      availableBudgetPoints,
      usedPolicyPoints,
      remainingBudgetPoints: Math.max(availableBudgetPoints - usedPolicyPoints, 0),
      isPending: Boolean(pendingInput) && index === allEntries.length - 1,
    }
  })
}

export function findAllowedPolicyPoints(policyHistory, simulationRows, year, sliders, key, requestedPoints) {
  const normalizedTarget = normalizePolicyMana(key, requestedPoints, policyHistory, sliders)

  for (let candidate = normalizedTarget; candidate >= 0; candidate -= 1) {
    const candidateValue = normalizePolicyMana(key, candidate, policyHistory, sliders)
    const candidateSliders = { ...sliders, [key]: candidateValue }
    const rows = buildBudgetRows(policyHistory, simulationRows, { year, sliders: candidateSliders })
    const budgetRow = rows[rows.length - 1]
    if (!budgetRow || budgetRow.usedPolicyPoints <= budgetRow.availableBudgetPoints) {
      return candidateValue
    }
  }

  return 0
}
