export const BASE_POLICY_BUDGET_POINTS = 10
export const POLICY_POINT_MAX = 10
export const HOUSE_MIGRATION_BUDGET_STEP_POINTS = 5
export const FLOOD_DAMAGE_BUDGET_POINT_USD = 2_000_000

export const POLICY_POINT_KEYS = [
  'planting_trees_amount',
  'house_migration_amount',
  'dam_levee_construction_cost',
  'paddy_dam_construction_cost',
  'agricultural_RnD_cost',
  'capacity_building_cost',
]

export function normalizePolicyPoints(value) {
  return Math.max(0, Math.min(POLICY_POINT_MAX, Math.round(Number(value) || 0)))
}

export function getUsedPolicyPoints(sliders = {}) {
  return POLICY_POINT_KEYS.reduce((sum, key) => sum + normalizePolicyPoints(sliders[key]), 0)
}

export function getFloodDamageForPeriod(rows = [], periodIndex) {
  if (periodIndex < 0) return 0

  const start = periodIndex * 25
  const end = start + 25
  return rows
    .slice(start, end)
    .reduce((sum, row) => sum + Math.max(Number(row?.['Flood Damage']) || 0, 0), 0)
}

export function getFloodBudgetReduction(floodDamage) {
  return Math.max(0, Math.floor(Math.max(Number(floodDamage) || 0, 0) / FLOOD_DAMAGE_BUDGET_POINT_USD))
}

export function getMigrationBudgetReduction(cumulativeMigrationPoints) {
  return Math.max(0, Math.floor(Math.max(Number(cumulativeMigrationPoints) || 0, 0) / HOUSE_MIGRATION_BUDGET_STEP_POINTS))
}

export function buildBudgetRows(policyHistory = [], simulationRows = [], pendingInput = null) {
  const completedEntries = Array.isArray(policyHistory) ? policyHistory : []
  const allEntries = pendingInput ? [...completedEntries, pendingInput] : completedEntries
  let previousMigrationPoints = 0

  return allEntries.map((entry, index) => {
    const sliders = entry?.sliders ?? {}
    const houseMigrationPoints = normalizePolicyPoints(sliders.house_migration_amount)
    const appliedFloodDamage = index === 0 ? 0 : getFloodDamageForPeriod(simulationRows, index - 1)
    const relocationPointsApplied = index === 0 ? 0 : previousMigrationPoints
    const floodReduction = getFloodBudgetReduction(appliedFloodDamage)
    const migrationReduction = getMigrationBudgetReduction(relocationPointsApplied)
    const availableBudgetPoints = Math.max(
      0,
      BASE_POLICY_BUDGET_POINTS - floodReduction - migrationReduction
    )
    const usedPolicyPoints = getUsedPolicyPoints(sliders)
    const totalBudgetReduction = floodReduction + migrationReduction
    const year = entry?.year
    const periodLabel = `${year ?? '-'} - ${Number.isFinite(year) ? year + 24 : '-'}`

    previousMigrationPoints = houseMigrationPoints

    return {
      year,
      periodLabel,
      sliders,
      houseMigrationPoints,
      appliedFloodDamage,
      relocationPointsApplied,
      floodReduction,
      migrationReduction,
      totalBudgetReduction,
      availableBudgetPoints,
      usedPolicyPoints,
      remainingBudgetPoints: Math.max(availableBudgetPoints - usedPolicyPoints, 0),
      isPending: Boolean(pendingInput) && index === allEntries.length - 1,
    }
  })
}

export function findAllowedPolicyPoints(policyHistory, simulationRows, year, sliders, key, requestedPoints) {
  const normalizedTarget = normalizePolicyPoints(requestedPoints)

  for (let candidate = normalizedTarget; candidate >= 0; candidate -= 1) {
    const candidateSliders = { ...sliders, [key]: candidate }
    const rows = buildBudgetRows(policyHistory, simulationRows, { year, sliders: candidateSliders })
    const budgetRow = rows[rows.length - 1]
    if (!budgetRow || budgetRow.usedPolicyPoints <= budgetRow.availableBudgetPoints) {
      return candidate
    }
  }

  return 0
}
