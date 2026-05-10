import { useState, useCallback } from 'react'
import { sliderToBackend } from '../data/policyEffects.js'

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
}

function buildDecisionVar({ year, sliders, rcpValue }) {
  return {
    year,
    cp_climate_params: rcpValue,
    planting_trees_amount:       sliderToBackend('planting_trees_amount',       sliders.planting_trees_amount ?? 1),
    house_migration_amount:      sliderToBackend('house_migration_amount',       sliders.house_migration_amount ?? 1),
    dam_levee_construction_cost: sliderToBackend('dam_levee_construction_cost',  sliders.dam_levee_construction_cost ?? 1),
    paddy_dam_construction_cost: sliderToBackend('paddy_dam_construction_cost',  sliders.paddy_dam_construction_cost ?? 1),
    capacity_building_cost:      sliderToBackend('capacity_building_cost',       sliders.capacity_building_cost ?? 1),
    transportation_invest:       sliderToBackend('transportation_invest',        sliders.transportation_invest ?? 1),
    agricultural_RnD_cost:       sliderToBackend('agricultural_RnD_cost',       sliders.agricultural_RnD_cost ?? 1),
  }
}

// Map data[0] keys (backend output) back to CurrentValues keys (backend input)
function extractState(prev, row) {
  return {
    ...prev,
    temp:                    row['Temperature (℃)']           ?? prev.temp,
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
  }
}

// Run 25 sequential simulation years and accumulate results
async function advance25Years({ currentValues, sliders, year, scenarioName, userName, rcpValue }) {
  let state = { ...currentValues }
  const yearlyResults = []

  for (let y = year; y < year + 25; y++) {
    const decisionVar = buildDecisionVar({ year: y, sliders, rcpValue })

    const res = await fetch(`${API}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_name: userName,
        scenario_name: scenarioName,
        mode: 'Sequential Decision-Making Mode',
        decision_vars: [decisionVar],
        num_simulations: 1,
        current_year_index_seq: state,
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
    llmCommentary: '',
    llmLoading: false,
    residentCouncil: null,
    residentCouncilLoading: false,
    residentCouncilError: false,
    residentInterviews: {},
    residentInterviewLoading: {},
    lastEvaluationRequest: null,
    gameView: 'simple',
    loading: false,
    error: null,
  })

  const startGame = useCallback(({ userName, teamName, mode, rcpValue }) => {
    const order = ['wildfire', 'tech_breakthrough']
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
      llmCommentary: '',
      llmLoading: false,
      residentCouncil: null,
      residentCouncilLoading: false,
      residentCouncilError: false,
      residentInterviews: {},
      residentInterviewLoading: {},
      lastEvaluationRequest: null,
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
      })

      const nextYear = s.year + 25
      const nextCycle = s.cycle + 1
      const newHistory = [...s.history, ...yearlyResults]
      const newPolicyHistory = [...(s.policyHistory ?? []), { year: s.year, sliders: { ...sliders } }]

      const consequenceKey = detectConsequenceEvent(yearlyResults)
      const order = s.exogenousOrder ?? ['wildfire', 'tech_breakthrough']
      const exogenousKey = order[(s.cycle - 1) % order.length]
      const finalState     = exogenousKey ? applyExogenousEffect(newState, exogenousKey) : newState

      const pendingEvents = []
      if (consequenceKey) pendingEvents.push({ key: consequenceKey, type: 'consequence' })
      if (exogenousKey)   pendingEvents.push({ key: exogenousKey,   type: 'exogenous'   })

      const nextPhase = nextYear > 2100 ? 'ending' : pendingEvents.length > 0 ? 'consequence' : 'report'
      const evalDecisionVar = buildDecisionVar({ year: s.year, sliders, rcpValue: s.rcpValue })
      const evaluationRequest = {
        stage_index: s.cycle,
        checkpoint_year: nextYear,
        period_start_year: s.year,
        period_end_year: nextYear - 1,
        decision_var: evalDecisionVar,
        simulation_rows: yearlyResults,
        language: 'ja',
      }

      setGameState(prev => ({
        ...prev,
        loading: false,
        llmCommentary: '',
        llmLoading: true,
        residentCouncil: null,
        residentCouncilLoading: true,
        residentCouncilError: false,
        residentInterviews: {},
        residentInterviewLoading: {},
        lastEvaluationRequest: evaluationRequest,
        currentValues: finalState,
        history: newHistory,
        policyHistory: newPolicyHistory,
        year: nextYear,
        cycle: nextCycle,
        phase: nextPhase,
        pendingEvents,
      }))

      // Fire detail-page evaluations in parallel. They are stored for DetailPanel only.
      fetch(`${API}/intermediate-evaluation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(evaluationRequest),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => setGameState(prev => ({ ...prev, llmCommentary: data.feedback ?? '', llmLoading: false })))
        .catch(() => setGameState(prev => ({ ...prev, llmLoading: false })))

      fetch(`${API}/resident-council`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(evaluationRequest),
      })
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(data => setGameState(prev => ({
          ...prev,
          residentCouncil: data,
          residentCouncilLoading: false,
          residentCouncilError: false,
        })))
        .catch(() => setGameState(prev => ({
          ...prev,
          residentCouncilLoading: false,
          residentCouncilError: true,
        })))

    } catch (err) {
      setGameState(prev => ({ ...prev, loading: false, error: err.message }))
    }
  }, [gameState])

  const requestResidentInterview = useCallback(async (personaKey, score) => {
    const request = gameState.lastEvaluationRequest
    if (!request || !personaKey) return

    setGameState(s => ({
      ...s,
      residentInterviewLoading: { ...(s.residentInterviewLoading ?? {}), [personaKey]: true },
    }))

    try {
      const res = await fetch(`${API}/resident-interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...request,
          persona_key: personaKey,
          score,
        }),
      })
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      setGameState(s => ({
        ...s,
        residentInterviews: {
          ...(s.residentInterviews ?? {}),
          [personaKey]: data.detailed_voice ?? '',
        },
        residentInterviewLoading: { ...(s.residentInterviewLoading ?? {}), [personaKey]: false },
      }))
    } catch {
      setGameState(s => ({
        ...s,
        residentInterviewLoading: { ...(s.residentInterviewLoading ?? {}), [personaKey]: false },
      }))
    }
  }, [gameState])

  const dismissReport = useCallback(() => {
    setGameState(s => ({ ...s, phase: 'game', gameView: 'detail' }))
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
        : s.year > 2100 ? 'ending' : 'report'
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
      llmCommentary: '',
      llmLoading: false,
      residentCouncil: null,
      residentCouncilLoading: false,
      residentCouncilError: false,
      residentInterviews: {},
      residentInterviewLoading: {},
      lastEvaluationRequest: null,
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
    requestResidentInterview,
    showComparison,
    backToEnding,
  }
}

// ── Consequence events (threshold-triggered) ──────────────────────────
function detectConsequenceEvent(yearlyResults) {
  if (!yearlyResults?.length) return null

  const last    = yearlyResults[yearlyResults.length - 1]
  const maxFlood = Math.max(...yearlyResults.map(r => r['Flood Damage'] ?? 0))
  const minYield = Math.min(...yearlyResults.map(r => r['Crop Yield']   ?? Infinity))

  if (maxFlood >= 1_500_000)                              return 'flood'
  if (minYield <= 2_500)                                  return 'drought'
  if ((last['Ecosystem Level'] ?? 100) <= 40)             return 'water_quality'
  for (const row of yearlyResults) {
    if ((row['Precipitation (mm)'] ?? 0) >= 1600 && (row['Forest Area'] ?? Infinity) <= 300)
      return 'landslide'
  }
  return null
}

// ── Exogenous events (one per cycle, order set at game start) ─────────
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
