/** Operation log store — see docs/operation_log_design.md */

import { finalScores, round1 } from '../data/resultScores.js'

const SCHEMA_VERSION = 1
const APP_VERSION = '0.1.0'
const API = import.meta.env.VITE_API_BASE || '/api'

let sessionMeta = null
let events = []
let seq = 0
let exportDone = false
let exportError = null
let surveyRecord = null
let intentSurveyRecords = []
let policyAllocationRecords = []
let contextRef = {
  phase: 'entry',
  cycle: null,
  year: null,
  gameView: null,
}

function nowIso() {
  return new Date().toISOString()
}

function newSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function sanitizeFilePart(value) {
  return String(value || 'anon')
    .trim()
    .replace(/[^\w\-]+/g, '_')
    .replace(/_+/g, '_')
    .slice(0, 40) || 'anon'
}

function formatStamp(date = new Date()) {
  const pad = n => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}` +
    `-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
  )
}

export function resetOperationLog() {
  sessionMeta = null
  events = []
  seq = 0
  exportDone = false
  exportError = null
  surveyRecord = null
  intentSurveyRecords = []
  policyAllocationRecords = []
  contextRef = { phase: 'entry', cycle: null, year: null, gameView: null }
}

/** Call when Entry screen mounts — allocates session_id for pre-start ethics events. */
export function beginEntryLogging() {
  resetOperationLog()
  sessionMeta = {
    session_id: newSessionId(),
    user_name: '',
    team_name: '',
    mode: null,
    rcp: null,
    ethics_consent: false,
    ethics_consent_at: null,
    client_started_at: null,
    app_version: APP_VERSION,
  }
  setLogContext({ phase: 'entry', cycle: null, year: null, gameView: null })
  return sessionMeta.session_id
}

export function setLogContext(partial = {}) {
  contextRef = { ...contextRef, ...partial }
}

export function getLogContext() {
  return { ...contextRef }
}

export function getSessionMeta() {
  return sessionMeta ? { ...sessionMeta } : null
}

export function getEvents() {
  return [...events]
}

export function isExportDone() {
  return exportDone
}

export function getExportError() {
  return exportError
}

export function getSurveyRecord() {
  return surveyRecord ? { ...surveyRecord, answers: { ...(surveyRecord.answers || {}) } } : null
}

/** Store survey answers as one bundled record and emit a single survey_submitted event. */
export function recordSurveySubmission(surveyPayload) {
  surveyRecord = {
    version: surveyPayload.version,
    submitted_at: surveyPayload.submitted_at || nowIso(),
    answers: { ...(surveyPayload.answers || {}) },
    research_focus: surveyPayload.research_focus || [],
  }
  setLogContext({ phase: 'survey' })
  emit('survey_submitted', {
    version: surveyRecord.version,
    submitted_at: surveyRecord.submitted_at,
    answers: surveyRecord.answers,
    research_focus: surveyRecord.research_focus,
  })
  return getSurveyRecord()
}

export function getIntentSurveyRecords() {
  return intentSurveyRecords.map(r => ({
    ...r,
    answers: { ...(r.answers || {}) },
    sliders: r.sliders ? { ...r.sliders } : null,
  }))
}

/** Record one per-cycle intent survey (after Advance) and emit intent_survey_submitted. */
export function recordIntentSurveySubmission(intentPayload) {
  const record = {
    version: intentPayload.version,
    submitted_at: intentPayload.submitted_at || nowIso(),
    cycle: intentPayload.cycle ?? null,
    year_range: intentPayload.year_range || null,
    answers: {
      target_objectives: [...(intentPayload.answers?.target_objectives || [])],
      free_text: String(intentPayload.answers?.free_text || ''),
    },
    sliders: intentPayload.sliders ? { ...intentPayload.sliders } : null,
  }
  intentSurveyRecords.push(record)
  emit('intent_survey_submitted', {
    version: record.version,
    submitted_at: record.submitted_at,
    cycle: record.cycle,
    year_range: record.year_range,
    answers: record.answers,
  }, {
    context: {
      phase: 'intent_survey',
      cycle: record.cycle,
      year: record.year_range?.start_year ?? null,
    },
  })
  return { ...record, answers: { ...record.answers } }
}

export function getPolicyAllocationRecords() {
  return policyAllocationRecords.map(r => ({
    ...r,
    policy_points: { ...(r.policy_points || {}) },
    year_range: r.year_range ? { ...r.year_range } : null,
  }))
}

/**
 * Record the policy-point allocation confirmed when the player presses Advance.
 * Stored both as an event and in the top-level policy_allocations array.
 */
export function recordPolicyAllocation({
  cycle,
  year,
  policyPoints,
  availableBudgetPoints = null,
  usedPolicyPoints = null,
  period = null,
} = {}) {
  const yearRange = period || {
    start_year: year,
    end_year: typeof year === 'number' ? year + 24 : null,
  }
  const points = { ...(policyPoints || {}) }
  const record = {
    recorded_at: nowIso(),
    cycle: cycle ?? null,
    year_range: yearRange,
    policy_points: points,
    available_budget_points: availableBudgetPoints,
    used_policy_points: usedPolicyPoints,
  }
  policyAllocationRecords.push(record)
  emit('policy_allocation', {
    cycle: record.cycle,
    year_range: record.year_range,
    policy_points: record.policy_points,
    available_budget_points: record.available_budget_points,
    used_policy_points: record.used_policy_points,
  }, {
    context: {
      phase: contextRef.phase || 'game',
      cycle: record.cycle,
      year: record.year_range?.start_year ?? year ?? null,
    },
  })
  return {
    ...record,
    policy_points: { ...record.policy_points },
    year_range: record.year_range ? { ...record.year_range } : null,
  }
}

export function emit(eventType, payload = {}, options = {}) {
  if (!sessionMeta) {
    beginEntryLogging()
  }
  const source = options.source || 'ui'
  const ctx = { ...contextRef, ...(options.context || {}) }
  seq += 1
  const event = {
    schema_version: SCHEMA_VERSION,
    session_id: sessionMeta.session_id,
    seq,
    ts_client: nowIso(),
    phase: ctx.phase ?? null,
    cycle: ctx.cycle ?? null,
    year: ctx.year ?? null,
    game_view: ctx.gameView ?? null,
    event_type: eventType,
    source,
    payload: payload ?? {},
  }
  events.push(event)
  return event
}

export function confirmSessionStart({
  userName,
  teamName,
  mode,
  rcpValue,
  ethicsConsentAt,
}) {
  if (!sessionMeta) beginEntryLogging()
  const startedAt = nowIso()
  sessionMeta = {
    ...sessionMeta,
    user_name: userName,
    team_name: teamName || '',
    mode,
    rcp: rcpValue,
    ethics_consent: true,
    ethics_consent_at: ethicsConsentAt || startedAt,
    client_started_at: startedAt,
    app_version: APP_VERSION,
  }
  setLogContext({ phase: 'game', cycle: 1, year: 2026, gameView: 'simple' })
  emit('session_start', {
    user_name: sessionMeta.user_name,
    team_name: sessionMeta.team_name,
    mode: sessionMeta.mode,
    rcp: sessionMeta.rcp,
    ethics_consent: true,
    ethics_consent_at: sessionMeta.ethics_consent_at,
    app_version: APP_VERSION,
  })
  emit('phase_enter', { phase: 'game' }, { source: 'system' })
  return getSessionMeta()
}

export function buildExportFilename(meta = sessionMeta, date = new Date()) {
  const userPart = sanitizeFilePart(meta?.user_name)
  const shortId = String(meta?.session_id || 'unknown').slice(0, 8)
  return `dapp-operation-log_${userPart}_${shortId}_${formatStamp(date)}.json`
}

export function buildHistorySummary(history = [], currentClimateHistory = []) {
  const scores = finalScores(history, currentClimateHistory)
  return {
    flood_score: round1(scores.floodScore),
    crop_score: round1(scores.cropScore),
    ecosystem_score: round1(scores.ecosystemScore),
    total_score: round1(scores.totalScore),
  }
}

export function buildExportObject({
  policyHistory = [],
  history = [],
  currentClimateHistory = [],
  cycleCount = 3,
  endedAtYear = 2100,
  filename,
  trigger = 'on_restart',
  success = true,
} = {}) {
  const exportedAt = nowIso()
  return {
    schema_version: SCHEMA_VERSION,
    exported_at: exportedAt,
    export: {
      filename,
      trigger,
      success,
      storage: 'backend',
    },
    session: getSessionMeta(),
    events: getEvents(),
    survey: getSurveyRecord(),
    intent_surveys: getIntentSurveyRecords(),
    policy_allocations: getPolicyAllocationRecords(),
    results: {
      policy_history: policyHistory,
      history_summary: buildHistorySummary(history, currentClimateHistory),
      cycle_count: cycleCount,
      ended_at_year: endedAtYear,
    },
  }
}

/**
 * Append session_end + session_export, then POST JSON to backend once per session.
 * Default trigger is on_restart (Play Again).
 */
export async function exportSessionJson({
  policyHistory,
  history,
  currentClimateHistory,
  cycleCount,
  endedAtYear,
  trigger = 'on_restart',
  force = false,
} = {}) {
  if (exportDone && !force) {
    return { ok: true, skipped: true, filename: null }
  }

  setLogContext({ phase: contextRef.phase || 'ending' })
  if (!events.some(e => e.event_type === 'session_end')) {
    emit('session_end', { reason: 'completed' }, { source: 'system' })
  }

  const filename = buildExportFilename()
  emit(
    'session_export',
    { filename, success: true, trigger, storage: 'backend' },
    { source: 'system' },
  )

  const payload = buildExportObject({
    policyHistory,
    history,
    currentClimateHistory,
    cycleCount,
    endedAtYear,
    filename,
    trigger,
    success: true,
  })

  try {
    const res = await fetch(`${API}/operation-logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const detail = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status} ${detail.slice(0, 200)}`)
    }
    const data = await res.json()
    const savedName = data.filename || filename
    const last = events[events.length - 1]
    if (last?.event_type === 'session_export') {
      last.payload = {
        ...last.payload,
        success: true,
        filename: savedName,
        path: data.path || null,
      }
    }
    exportDone = true
    exportError = null
    return { ok: true, filename: savedName, path: data.path || null }
  } catch (err) {
    const last = events[events.length - 1]
    if (last?.event_type === 'session_export') {
      last.payload = { ...last.payload, success: false }
    }
    exportError = err?.message || String(err)
    return { ok: false, error: exportError, filename }
  }
}
