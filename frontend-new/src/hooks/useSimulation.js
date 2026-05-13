import { useState, useCallback } from 'react'
import { sliderToBackend } from '../data/policyEffects.js'
import {
  buildBudgetRows,
  getCumulativePolicyMana,
  MANA_JPY_PER_YEAR,
  TURN_YEARS,
  COST_PER_MIGRATION,
  INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR,
  MIGRATION_INFRA_PENALTY_START_MANA,
} from '../data/budget.js'

const API = '/api'

const INITIAL_VALUES = {
  temp: 15.5,
  precip: 1700.0,
  municipal_demand: 100.0,
  available_water: 2000.0,
  crop_yield: 4500.0,
  hot_days: 30.0,
  extreme_precip_freq: 0.1,
  ecosystem_level: 1000.0,
  levee_level: 0.0,
  high_temp_tolerance_level: 0.0,
  forest_area: 5000.0,
  planting_history: {},
  urban_level: 0.0,
  resident_capacity: 0.0,
  transportation_level: 100.0,
  levee_investment_total: 0.0,
  RnD_investment_total: 0.0,
  risky_house_total: 10000.0,
  non_risky_house_total: 0.0,
  resident_burden: 0.0,
  biodiversity_level: 0.0,
  paddy_dam_area: 0.0,
  cumulative_migrated_houses: 0.0,
  cumulative_house_migration_mana: 0.0,
  initial_risky_house_total: 10000.0,
  initial_crop_yield: 4500.0,
  events_state: {},
  available_budget_mana: 10.0,
  population_budget_multiplier: 1.0,
  population_decline_penalty_mana: 0.0,
  migration_infra_penalty_mana: 0.0,
  flood_recovery_penalty_mana: 0.0,
  last_25y_avg_flood_damage_jpy: 0.0,
}

// Map data[0] keys (backend output) back to CurrentValues keys (backend input)
function extractState(prev, row) {
  return {
    ...prev,
    temp:                    row['Temperature (ﾂｰC)'] ?? row['Temperature (邃・'] ?? row.temp ?? prev.temp,
    precip:                  row['Precipitation (mm)']         ?? prev.precip,
    available_water:         row['available_water']            ?? prev.available_water,
    crop_yield:              row['Crop Yield']                 ?? prev.crop_yield,
    municipal_demand:        row['Municipal Demand']           ?? prev.municipal_demand,
    hot_days:                row['Hot Days']                   ?? prev.hot_days,
    extreme_precip_freq:     row['Extreme Precip Frequency']   ?? prev.extreme_precip_freq,
    ecosystem_level:         row['Ecosystem Level']            ?? prev.ecosystem_level,
    levee_level:             row['Levee Level']                ?? prev.levee_level,
    high_temp_tolerance_level: row['High Temp Tolerance Level'] ?? prev.high_temp_tolerance_level,
    forest_area:             row['Forest Area']                ?? prev.forest_area,
    planting_history:        row['planting_history']           ?? prev.planting_history,
    urban_level:             row['Urban Level']                ?? prev.urban_level,
    resident_capacity:       row['Resident capacity']          ?? prev.resident_capacity,
    transportation_level:    row['transportation_level']       ?? prev.transportation_level,
    levee_investment_total:  row['Levee investment total']     ?? prev.levee_investment_total,
    RnD_investment_total:    row['RnD investment total']       ?? prev.RnD_investment_total,
    risky_house_total:       row['risky_house_total']          ?? prev.risky_house_total,
    non_risky_house_total:   row['non_risky_house_total']      ?? prev.non_risky_house_total,
    resident_burden:         row['Resident Burden']            ?? prev.resident_burden,
    biodiversity_level:      row['Ecosystem Level']            ?? prev.biodiversity_level,
    paddy_dam_area:          row['paddy_dam_area']             ?? prev.paddy_dam_area,
    cumulative_migrated_houses: row['cumulative_migrated_houses'] ?? prev.cumulative_migrated_houses,
    cumulative_house_migration_mana: row['cumulative_house_migration_mana'] ?? prev.cumulative_house_migration_mana,
    initial_risky_house_total: row['initial_risky_house_total'] ?? prev.initial_risky_house_total,
    initial_crop_yield:      row['initial_crop_yield']          ?? prev.initial_crop_yield,
    events_state:            row['events_state']                ?? prev.events_state,
    available_budget_mana:   row['available_budget_mana']       ?? prev.available_budget_mana,
    population_budget_multiplier: row['population_budget_multiplier'] ?? prev.population_budget_multiplier,
    population_decline_penalty_mana: row['population_decline_penalty_mana'] ?? prev.population_decline_penalty_mana,
    migration_infra_penalty_mana: row['migration_infra_penalty_mana'] ?? prev.migration_infra_penalty_mana,
    flood_recovery_penalty_mana: row['flood_recovery_penalty_mana'] ?? prev.flood_recovery_penalty_mana,
    last_25y_avg_flood_damage_jpy: row['last_25y_avg_flood_damage_jpy'] ?? prev.last_25y_avg_flood_damage_jpy,
  }
}

// Run 25 sequential simulation years and accumulate results
async function advance25Years({ currentValues, sliders, year, scenarioName, userName, rcpValue, policyHistory, history }) {
  let state = { ...currentValues }
  const yearlyResults = []
  const budgetRows = buildBudgetRows(policyHistory, history, { year, sliders })
  const budgetRow = budgetRows[budgetRows.length - 1]

  for (let y = year; y < year + 25; y++) {
    const decisionVar = {
      year: y,
      cp_climate_params: rcpValue,
      planting_trees_amount:       sliderToBackend('planting_trees_amount',       sliders.planting_trees_amount ?? 0),
      house_migration_amount:      sliderToBackend('house_migration_amount',       sliders.house_migration_amount ?? 0),
      dam_levee_construction_cost: sliderToBackend('dam_levee_construction_cost',  sliders.dam_levee_construction_cost ?? 0),
      paddy_dam_construction_cost: sliderToBackend('paddy_dam_construction_cost',  sliders.paddy_dam_construction_cost ?? 0),
      capacity_building_cost:      sliderToBackend('capacity_building_cost',       sliders.capacity_building_cost ?? 0),
      transportation_invest:       sliderToBackend('transportation_invest',        sliders.transportation_invest ?? 0),
      agricultural_RnD_cost:       sliderToBackend('agricultural_RnD_cost',       sliders.agricultural_RnD_cost ?? 0),
    }

    const res = await fetch(`${API}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_name: userName,
        scenario_name: scenarioName,
        mode: 'Sequential Decision-Making Mode',
        decision_vars: [decisionVar],
        num_simulations: 1,
        current_year_index_seq: {
          ...state,
          last_25y_avg_flood_damage_jpy: budgetRow?.appliedFloodDamage ?? 0,
          available_budget_mana: budgetRow?.availableBudgetPoints ?? 10,
          population_budget_multiplier: budgetRow?.populationMultiplier ?? 1,
          population_decline_penalty_mana: budgetRow?.populationPenaltyMana ?? 0,
          migration_infra_penalty_mana: budgetRow?.migrationReduction ?? 0,
          flood_recovery_penalty_mana: budgetRow?.floodReduction ?? 0,
        },
      }),
    })

    if (!res.ok) {
      const detail = await res.text().catch(() => '')
      throw new Error(`Year ${y}: ${res.status} ${detail.slice(0, 200)}`)
    }
    const json = await res.json()
    const row = json.data[0]

    // FastAPI's response_model strips current_values, so extract next state from data[0]
    state = extractState(state, row)
    yearlyResults.push({ year: y, ...row })
  }

  return { newState: state, yearlyResults }
}

export function useSimulation() {
  const [gameState, setGameState] = useState({
    phase: 'entry',       // 'entry' | 'game' | 'consequence' | 'ending'
    year: 2026,
    cycle: 1,
    userName: '',
    teamName: '',
    mode: 'upstream',     // 'upstream' | 'downstream' | 'both'
    rcpValue: 4.5,
    currentValues: INITIAL_VALUES,
    history: [],          // [{year, ...indicators}] accumulated across all cycles
    policyHistory: [],    // [{year, sliders}] completed policy allocations
    blockScores: [],
    pendingEvents: [],
    emittedEventKeys: [],
    llmCommentary: '',
    llmLoading: false,
    gameView: 'simple',
    loading: false,
    error: null,
  })

  const startGame = useCallback(({ userName, teamName, mode, rcpValue }) => {
    const order = []
    setGameState(s => ({
      ...s,
      phase: 'game',
      userName,
      teamName,
      mode,
      rcpValue: rcpValue ?? 4.5,
      currentValues: INITIAL_VALUES,
      history: [],
      policyHistory: [],
      emittedEventKeys: [],
      year: 2026,
      cycle: 1,
      exogenousOrder: order,
    }))
  }, [])

  const advanceCycle = useCallback(async (sliders) => {
    setGameState(s => ({ ...s, loading: true, error: null }))

    try {
      const s = gameState
      const { newState, yearlyResults } = await advance25Years({
        currentValues: s.currentValues,
        sliders,
        year: s.year,
        scenarioName: `${s.userName}_${s.mode}_cycle${s.cycle}`,
        userName: s.userName,
        rcpValue: s.rcpValue,
        policyHistory: s.policyHistory ?? [],
        history: s.history ?? [],
      })

      const nextYear = s.year + 25
      const nextCycle = s.cycle + 1
      const newHistory = [...s.history, ...yearlyResults]
      const newPolicyHistory = [...(s.policyHistory ?? []), { year: s.year, sliders: { ...sliders } }]

      const modelEvents = dedupeEvents([
        ...collectPolicyStartEvents(sliders, s.policyHistory ?? [], s.year),
        ...collectTurnEvents(yearlyResults),
      ])
      const consequenceKey = modelEvents.length > 0 ? null : detectConsequenceEvent(yearlyResults)
      const order = s.exogenousOrder ?? []
      const exogenousKey = order.length > 0 ? order[(s.cycle - 1) % order.length] : null
      const finalState     = exogenousKey ? applyExogenousEffect(newState, exogenousKey) : newState

      const emitted = new Set(s.emittedEventKeys ?? [])

      const rawPendingEvents = [...modelEvents]
      if (consequenceKey?.key && !emitted.has(consequenceKey.key)) {
        rawPendingEvents.push({ ...consequenceKey, type: 'consequence' })
      }
      if (exogenousKey) {
        rawPendingEvents.push({ key: exogenousKey, type: 'exogenous' })
      }

      const filteredPendingEvents = filterConsequenceEvents(rawPendingEvents, {
        cycle: s.cycle,
        turnStartYear: s.year,
        emittedEventKeys: emitted,
      }).sort(compareConsequenceEvents)

      const queuedEvents = filteredPendingEvents.map((event, index) => ({
        ...event,
        queueIndex: index + 1,
        queueTotal: filteredPendingEvents.length,
      }))

      const nextEmittedEventKeys = [
        ...new Set([
          ...emitted,
          ...filteredPendingEvents
            .filter(shouldRememberEventKey)
            .map(buildPersistentEventKey),
        ]),
      ]

      // 最終ターンでも、イベント表示または25年間レポートを見せてから ending に進む。
      // 2076-2100 の結果を見せずに即終了しないようにする。
      const nextPhase = queuedEvents.length > 0 ? 'consequence' : 'report'

      setGameState(prev => ({
        ...prev,
        loading: false,
        llmCommentary: '',
        llmLoading: true,
        currentValues: finalState,
        history: newHistory,
        policyHistory: newPolicyHistory,
        year: nextYear,
        cycle: nextCycle,
        phase: nextPhase,
        pendingEvents: queuedEvents,
        emittedEventKeys: nextEmittedEventKeys,
      }))

      // Fire LLM evaluation in parallel 窶・does not block phase transition
      const evalDecisionVar = {
        year: s.year,
        cp_climate_params: s.rcpValue,
        planting_trees_amount:       sliderToBackend('planting_trees_amount',       sliders.planting_trees_amount ?? 0),
        house_migration_amount:      sliderToBackend('house_migration_amount',       sliders.house_migration_amount ?? 0),
        dam_levee_construction_cost: sliderToBackend('dam_levee_construction_cost',  sliders.dam_levee_construction_cost ?? 0),
        paddy_dam_construction_cost: sliderToBackend('paddy_dam_construction_cost',  sliders.paddy_dam_construction_cost ?? 0),
        capacity_building_cost:      sliderToBackend('capacity_building_cost',       sliders.capacity_building_cost ?? 0),
        transportation_invest:       sliderToBackend('transportation_invest',        sliders.transportation_invest ?? 0),
        agricultural_RnD_cost:       sliderToBackend('agricultural_RnD_cost',       sliders.agricultural_RnD_cost ?? 0),
      }
      fetch(`${API}/intermediate-evaluation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stage_index: s.cycle,
          checkpoint_year: nextYear,
          period_start_year: s.year,
          period_end_year: nextYear - 1,
          decision_var: evalDecisionVar,
          simulation_rows: yearlyResults,
          language: 'ja',
        }),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => setGameState(prev => ({ ...prev, llmCommentary: data.feedback ?? '', llmLoading: false })))
        .catch(() => setGameState(prev => ({ ...prev, llmLoading: false })))

    } catch (err) {
      setGameState(prev => ({ ...prev, loading: false, error: err.message }))
    }
  }, [gameState])

  const dismissReport = useCallback(() => {
    setGameState(s => ({
      ...s,
      phase: s.year > 2100 ? 'ending' : 'game',
      gameView: 'detail',
    }))
  }, [])

  const showComparison = useCallback(() => {
    setGameState(s => ({ ...s, phase: 'comparison' }))
  }, [])

  const backToEnding = useCallback(() => {
    setGameState(s => ({ ...s, phase: 'ending' }))
  }, [])

  const setGameView = useCallback((v) => {
    setGameState(s => ({ ...s, gameView: v }))
  }, [])

  const dismissConsequence = useCallback(() => {
    setGameState(s => {
      const remaining = s.pendingEvents.slice(1)
      const nextPhase = remaining.length > 0
        ? 'consequence'
        : 'report'
      return { ...s, pendingEvents: remaining, phase: nextPhase }
    })
  }, [])

  const restart = useCallback(() => {
    setGameState(s => ({
      ...s,
      phase: 'entry',
      year: 2026,
      cycle: 1,
      history: [],
      policyHistory: [],
      currentValues: INITIAL_VALUES,
      pendingEvents: [],
      emittedEventKeys: [],
    }))
  }, [])

  return {
    gameState,
    startGame,
    advanceCycle,
    dismissReport,
    dismissConsequence,
    restart,
    setGameView,
    showComparison,
    backToEnding,
  }
}

// 笏笏 Consequence events (threshold-triggered) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
function detectConsequenceEvent(yearlyResults) {
  if (!yearlyResults?.length) return null

  const last    = yearlyResults[yearlyResults.length - 1]
  const maxFlood = Math.max(...yearlyResults.map(r => r['Flood Damage JPY'] ?? ((r['Flood Damage'] ?? 0) * 150)))
  const minYield = Math.min(...yearlyResults.map(r => r['Crop Yield']   ?? Infinity))

  if (maxFlood >= 100_000_000) return { key: 'flood', value: maxFlood }
  if (minYield <= 2_500) return { key: 'drought', value: minYield }
  if ((last['Ecosystem Level'] ?? 100) <= 40) return { key: 'water_quality', value: last['Ecosystem Level'] }
  return null
}

function collectTurnEvents(yearlyResults = []) {
  const events = []

  yearlyResults.forEach(row => {
    const backendEvents = Array.isArray(row.events) ? row.events : (Array.isArray(row.Events) ? row.Events : [])

    backendEvents.forEach((ev, index) => {
      if (!ev || ev.category === 'urban') return

      // levee_completed は levee_20mm_step_{n} と重複しやすいので表示しない。
      // 表示する堤防イベントは levee_started と levee_20mm_step_{n} に絞る。
      if (ev.id === 'levee_completed') return

      const category = ev.category ?? 'event'
      const title = ev.title ?? 'イベント'

      events.push({
        key: category,
        type: 'model_event',
        id: ev.id,
        year: ev.year ?? row.year,
        title,
        message: ev.message ?? '',
        severity: ev.severity ?? 'warning',
        category,
        related_policy: ev.related_policy,
        metric: ev.metric,
        value: ev.value,
        threshold: ev.threshold,
        sortIndex: index,
      })
    })
  })

  return events.sort((a, b) => (a.year - b.year) || (a.sortIndex - b.sortIndex))
}

function collectPolicyStartEvents(sliders = {}, policyHistory = [], year) {
  const previousUse = new Set()
  policyHistory.forEach(entry => {
    Object.entries(entry?.sliders ?? {}).forEach(([key, value]) => {
      if (sliderToBackend(key, value) > 0) previousUse.add(key)
    })
  })

  const policyEvents = buildPolicyStartEvents(sliders, policyHistory)
  return Object.entries(policyEvents).flatMap(([key, event], index) => {
    if (previousUse.has(key) || sliderToBackend(key, sliders[key] ?? 0) <= 0) return []
    return [{
      key: 'policy_effect',
      type: 'model_event',
      id: event.id,
      year,
      title: event.title,
      message: event.message,
      severity: 'success',
      category: 'policy_effect',
      related_policy: key,
      sortIndex: -100 + index,
    }]
  })
}

function buildPolicyStartEvents(sliders = {}, policyHistory = []) {
  const migrationMana = sliderToBackend('house_migration_amount', sliders.house_migration_amount ?? 0)
  const paddyMana = sliderToBackend('paddy_dam_construction_cost', sliders.paddy_dam_construction_cost ?? 0)
  const previousMigrationMana = getCumulativePolicyMana(policyHistory, 'house_migration_amount')
  const housesPerTurnMana = MANA_JPY_PER_YEAR * TURN_YEARS / COST_PER_MIGRATION
  const movedHouses = Math.round(migrationMana * housesPerTurnMana)
  const exposureReductionPct = Math.min(100, (movedHouses / 10_000) * 100)
  const previousChargeable = Math.max(0, previousMigrationMana - MIGRATION_INFRA_PENALTY_START_MANA)
  const nextChargeable = Math.max(0, previousMigrationMana + migrationMana - MIGRATION_INFRA_PENALTY_START_MANA)
  const migrationBudgetPenalty = (nextChargeable - previousChargeable) * housesPerTurnMana * INFRA_COST_PER_MIGRATED_HOUSE_PER_YEAR / MANA_JPY_PER_YEAR
  const paddyAreaHa = Math.round(paddyMana * MANA_JPY_PER_YEAR * TURN_YEARS / 1_000_000 / 1.5)
  const paddyLevelMm = Math.min(10, paddyAreaHa / 2000 * 10)

  return {
    planting_trees_amount: {
      id: 'forest_investment_started',
      title: '植林・森林保全を開始しました',
      message: '植林は約30年遅れて効果が出ます。2026年に始めた分は2056年のターン開始後に、保水力と生態系の改善イベントとして表示されます。',
    },
    house_migration_amount: {
      id: 'relocation_effect_started',
      title: '住宅移転を開始しました',
      message: `この25年で約${movedHouses.toLocaleString()}戸を高リスク区域から移転します。浸水にさらされる住宅は約${exposureReductionPct.toFixed(1)}%減り、大雨時の洪水被害を直接下げます。一方で将来の公共インフラ維持費により、次ターン以降の予算制約は約${migrationBudgetPenalty.toFixed(2)}マナ悪化します。`,
    },
    dam_levee_construction_cost: {
      id: 'levee_started',
      title: '堤防・河川改修を開始しました',
      message: '累積投資が進み、防御水準が20mm上がるごとにイベントを表示します。20mm強化ごとに、代表的な180mm豪雨の越流水を約25%減らします。',
    },
    paddy_dam_construction_cost: {
      id: 'paddy_dam_started',
      title: '田んぼダムを開始しました',
      message: `この25年で約${paddyAreaHa.toLocaleString()}ha、貯留効果は約${paddyLevelMm.toFixed(1)}mm分増えます。1マナあたり約333ha、180mm豪雨の越流水を約2%減らし、農作物生産には最大1%程度の小さな負担があります。`,
    },
    capacity_building_cost: {
      id: 'resident_capacity_started',
      title: '避難訓練を開始しました',
      message: '継続すると10から15年ほどで住民対応力の閾値を超えます。避難判断と初動対応が改善し、中小規模の浸水被害を抑えやすくなります。',
    },
    agricultural_RnD_cost: {
      id: 'rnd_started',
      title: '農業R&Dを開始しました',
      message: '高温対応品種と栽培技術の研究を始めます。高温耐性が0.2℃分上がるたびにイベントを表示し、作物生産高の低下を抑えます。',
    },
  }
}
function dedupeEvents(events = []) {
  const seen = new Set()
  return events.filter(event => {
    const key = `${event.year}:${event.id ?? event.key}:${event.category ?? ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function getEventId(event = {}) {
  return String(event.id ?? event.key ?? event.title ?? '')
}

function getEventYear(event = {}, fallbackYear = 2026) {
  const year = Number(event.year)
  return Number.isFinite(year) ? year : fallbackYear
}

function getTurnIndexByYear(year) {
  if (year <= 2050) return 1
  if (year <= 2075) return 2
  return 3
}

function isExtremeRainEventId(id) {
  // extreme_rain_record_ は extreme_rain_ でも始まるため、先に明示する。
  if (id.startsWith('extreme_rain_record_')) return true

  // extreme_rain_frequency_ は意味が重複するので表示しない。
  // startsWith('extreme_rain_') だけだと誤って通してしまう。
  if (id.startsWith('extreme_rain_frequency_')) return false

  return id.startsWith('extreme_rain_')
}

function isHiddenEventId(id) {
  if (id.startsWith('heavy_rain_')) return true
  if (id.startsWith('extreme_rain_frequency_')) return true

  if (id === 'budget_low') return true
  if (id === 'budget_critical') return true
  if (id === 'migration_budget_pressure') return true

  if (id === 'resident_capacity_low_turn2_summary') return false
  if (id === 'high_risk_houses_unmanaged_turn2_summary') return false

  // 末尾に _{year} が付く場合と、付かない場合の両方を落とす。
  if (id === 'resident_capacity_low') return true
  if (id.startsWith('resident_capacity_low_')) return true

  if (id === 'high_risk_houses_unmanaged') return true
  if (id.startsWith('high_risk_houses_unmanaged_')) return true

  return false
}

function getOncePerTurnGroup(id) {
  if (id.startsWith('flood_damage_')) return 'flood_damage'
  if (id.startsWith('major_flood_damage_')) return 'flood_damage'
  if (id.startsWith('severe_flood_damage_')) return 'flood_damage'

  if (id.startsWith('flood_policy_gap_')) return 'flood_policy_gap'

  if (id.startsWith('crop_production_low')) return 'crop_production'
  if (id.startsWith('crop_production_critical')) return 'crop_production'

  if (id.startsWith('ecosystem_low')) return 'ecosystem'
  if (id.startsWith('ecosystem_critical')) return 'ecosystem'

  if (id.startsWith('forest_area_low')) return 'forest'
  if (id.startsWith('forest_degradation')) return 'forest'
  if (id === 'forest_policy_needed') return 'forest'

  return null
}

function isOneShotEventId(id) {
  const exactOneShotIds = new Set([
    'paddy_dam_started',
    'paddy_dam_5mm',
    'paddy_dam_full',

    'rnd_started',

    'forest_effect_started',
    'forest_effect_100ha',
    'forest_effect_300ha',

    'resident_capacity_improved',
    'resident_capacity_high',

    // policy start events from the frontend
    'forest_investment_started',
    'relocation_effect_started',
    'levee_started',
    'resident_capacity_started',
  ])

  if (exactOneShotIds.has(id)) return true
  if (/^levee_20mm_step_\d+$/.test(id)) return true
  if (/^rnd_tolerance_improved_\d+$/.test(id)) return true

  return false
}

function buildPersistentEventKey(event = {}) {
  const id = getEventId(event)

  if (event.type === 'consequence') {
    return event.key
  }

  if (isOneShotEventId(id)) {
    return `oneshot:${id}`
  }

  return `${event.type ?? 'event'}:${id}`
}

function shouldRememberEventKey(event = {}) {
  const id = getEventId(event)

  if (event.type === 'consequence') return true
  if (isOneShotEventId(id)) return true

  return false
}

function filterConsequenceEvents(events = [], options = {}) {
  const {
    cycle = 1,
    turnStartYear = 2026,
    emittedEventKeys = new Set(),
  } = options

  const usedTurnGroups = new Set()
  const filtered = []

  events.forEach(event => {
    const id = getEventId(event)
    const year = getEventYear(event, turnStartYear)
    const turnIndex = getTurnIndexByYear(year)

    if (!id) return

    // 1. 表示しないイベントを先に落とす。
    // extreme_rain_frequency_ のように extreme_rain_ で始まるが不要なものを確実に除外する。
    if (isHiddenEventId(id)) {
      return
    }

    // 2. 極端豪雨・記録的豪雨は必ず表示する。
    if (isExtremeRainEventId(id)) {
      filtered.push(event)
      return
    }

    // 3. 農業生産低下イベントは早すぎる発火を防ぐ
    // 2026年時点などで出ると不自然なので、2050年より前は表示しない
    if (
      year < 2050 &&
      (id.startsWith('crop_production_low') || id.startsWith('crop_production_critical'))
    ) {
      return
    }

    // 4. 一度きりの政策効果イベント
    if (isOneShotEventId(id)) {
      const persistentKey = `oneshot:${id}`
      if (emittedEventKeys.has(persistentKey)) return

      filtered.push(event)
      return
    }

    // 5. 洪水・農業・生態系・森林・政策不足は1ターン1回まで
    const group = getOncePerTurnGroup(id)
    if (group) {
      const turnGroupKey = `${group}:turn${turnIndex}`

      if (usedTurnGroups.has(turnGroupKey)) return
      usedTurnGroups.add(turnGroupKey)

      filtered.push(event)
      return
    }

    // 6. その他はそのまま通す
    filtered.push(event)
  })

  return filtered
}

function compareConsequenceEvents(a, b) {
  const ay = getEventYear(a, a?.year ?? 0)
  const by = getEventYear(b, b?.year ?? 0)
  if (ay !== by) return ay - by

  const ap = getEventDisplayPriority(getEventId(a))
  const bp = getEventDisplayPriority(getEventId(b))
  if (ap !== bp) return ap - bp

  return (a.sortIndex ?? 0) - (b.sortIndex ?? 0)
}

function getEventDisplayPriority(id = '') {
  if (id === 'forest_investment_started') return -20
  if (id === 'relocation_effect_started') return -19
  if (id === 'levee_started') return -18
  if (id === 'paddy_dam_started') return -17
  if (id === 'resident_capacity_started') return -16
  if (id === 'rnd_started') return -15

  if (isExtremeRainEventId(id) || id.startsWith('heavy_rain_')) return 0
  if (id.startsWith('flood_damage_') || id.startsWith('major_flood_damage_') || id.startsWith('severe_flood_damage_')) return 10
  if (id === 'resident_capacity_low_turn2_summary') return 20
  if (id === 'high_risk_houses_unmanaged_turn2_summary') return 21

  return 50
}

function applyExogenousEffect(state, key) {
  if (key === 'wildfire') {
    return { ...state, forest_area: (state.forest_area ?? 0) * 0.85 }
  }
  if (key === 'tech_breakthrough') {
    return {
      ...state,
      high_temp_tolerance_level: (state.high_temp_tolerance_level ?? 0) + 0.15,
      available_water:           (state.available_water           ?? 0) + 300,
    }
  }
  return state
}

