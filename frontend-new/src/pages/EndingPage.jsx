import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './EndingPage.module.css'

const API = '/api'

function classifyStrategy(history) {
  if (history.length === 0) return 'balanced'
  const avgEcosystem  = history.reduce((a, r) => a + (r['Ecosystem Level'] ?? 0), 0) / history.length
  const avgFloodDamage = history.reduce((a, r) => a + (r['Flood Damage'] ?? 0), 0) / history.length
  if (avgEcosystem > 70) return 'eco'
  if (avgFloodDamage < 5e6) return 'engineer'
  return 'balanced'
}

function getCityOutcome(history) {
  if (history.length === 0) return 'surviving'
  const last = history[history.length - 1]
  if ((last['Crop Yield'] ?? 0) > 3500 && (last['Ecosystem Level'] ?? 0) > 70) return 'thriving'
  if ((last['Flood Damage'] ?? 0) > 3e8) return 'struggling'
  return 'surviving'
}

const PROFILE_ICONS = { eco: '🌿', engineer: '🛡', balanced: '⚖️' }
const CITY_COLORS   = { thriving: '#4a8c5c', surviving: '#8c6b3d', struggling: '#8c3d3d' }

function formatFloodDamage(value) {
  const amount = Number(value) || 0
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M`
  if (amount >= 1_000) return `${Math.round(amount / 1_000)}K`
  return `${Math.round(amount)}`
}

function sumRows(rows, key) {
  return rows.reduce((total, row) => total + (Number(row?.[key]) || 0), 0)
}

function avgRows(rows, key) {
  return rows.length ? sumRows(rows, key) / rows.length : 0
}

function buildComparisonSummary(history) {
  const rows = Array.isArray(history) ? history : []
  const last = rows[rows.length - 1] ?? {}
  const flood = sumRows(rows, 'Flood Damage')
  const cropYield = Number(last['Crop Yield']) || avgRows(rows, 'Crop Yield')
  const ecosystem = Number(last['Ecosystem Level']) || avgRows(rows, 'Ecosystem Level')
  const burden = avgRows(rows, 'Resident Burden')
  const floodScore = Math.max(0, 100 - (flood / 30_000_000) * 100)
  const yieldScore = Math.max(0, Math.min(100, (cropYield / 5000) * 100))
  const ecoScore = Math.max(0, Math.min(100, ecosystem))
  const burdenScore = Math.max(0, 100 - (burden / 5000) * 100)

  return {
    cumulativeFloodDamage: flood,
    finalCropYield: cropYield,
    finalEcosystemLevel: ecosystem,
    averageResidentBurden: burden,
    totalScore: (floodScore + yieldScore + ecoScore + burdenScore) / 4,
  }
}

export default function EndingPage({ sim, onRestart, onCompare }) {
  const { t } = useTranslation()
  const { history, userName, mode } = sim.gameState
  const [personaCommentary, setPersonaCommentary] = useState(null)
  const [personaLoading, setPersonaLoading] = useState(false)
  const [personaError, setPersonaError] = useState(false)
  const savedComparisonRef = useRef(false)
  const strategyKey = classifyStrategy(history)
  const outcomeKey  = getCityOutcome(history)
  const last = history[history.length - 1] ?? {}
  const cumulativeFloodDamage = history.reduce(
    (sum, row) => sum + Math.max(Number(row?.['Flood Damage']) || 0, 0),
    0
  )
  const comparisonSummary = buildComparisonSummary(history)

  const headline = t('ending.headline').replace('{name}', userName)

  useEffect(() => {
    if (!history.length) return

    let cancelled = false
    setPersonaLoading(true)
    setPersonaError(false)

    fetch(`${API}/final-commentary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(history),
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        if (!cancelled) setPersonaCommentary(data)
      })
      .catch(() => {
        if (!cancelled) setPersonaError(true)
      })
      .finally(() => {
        if (!cancelled) setPersonaLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [history])

  useEffect(() => {
    if (!history.length || savedComparisonRef.current) return
    savedComparisonRef.current = true

    fetch(`${API}/comparison-results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_name: userName || 'Guest',
        mode,
        cumulative_flood_damage: comparisonSummary.cumulativeFloodDamage,
        final_crop_yield: comparisonSummary.finalCropYield,
        final_ecosystem_level: comparisonSummary.finalEcosystemLevel,
        average_resident_burden: comparisonSummary.averageResidentBurden,
        total_score: comparisonSummary.totalScore,
      }),
    }).catch(() => {})
  }, [comparisonSummary, history.length, mode, userName])

  return (
    <div className={s.page}>
      <div className={s.content}>
        <div className={s.yearTag}>{t('ending.tag')}</div>
        <h1 className={s.headline}>{headline}</h1>

        <div className={s.profileCard}>
          <span className={s.profileIcon}>{PROFILE_ICONS[strategyKey]}</span>
          <div>
            <div className={s.profileEn}>{t(`profile.${strategyKey}.en`)}</div>
            <div className={s.profileLabel}>{t(`profile.${strategyKey}.label`)}</div>
            <p className={s.profileDesc}>{t(`profile.${strategyKey}.desc`)}</p>
          </div>
        </div>

        <div className={s.cityCard} style={{ borderColor: CITY_COLORS[outcomeKey] }}>
          <div className={s.cityLabel} style={{ color: CITY_COLORS[outcomeKey] }}>
            {t(`city.${outcomeKey}.label`)}
          </div>
          <p className={s.cityText}>{t(`city.${outcomeKey}.text`)}</p>
        </div>

        <div className={s.personaCard}>
          <div className={s.personaLabel}>{t('ending.persona.title')}</div>
          {personaLoading && <p className={s.personaText}>{t('ending.persona.loading')}</p>}
          {personaError && <p className={s.personaText}>{t('ending.persona.error')}</p>}
          {!personaLoading && !personaError && personaCommentary && (
            <>
              <div className={s.personaMeta}>{personaCommentary.agent_name}</div>
              <p className={s.personaText}>{personaCommentary.text}</p>
            </>
          )}
        </div>

        <div className={s.stats}>
          <div className={s.stat}>
            <div className={s.statVal}>{formatFloodDamage(cumulativeFloodDamage)}</div>
            <div className={s.statLabel}>{t('ending.stats.flood')}</div>
          </div>
          <div className={s.stat}>
            <div className={s.statVal}>{(last['Crop Yield'] ?? 0).toFixed(0)}</div>
            <div className={s.statLabel}>{t('ending.stats.yield')}</div>
          </div>
          <div className={s.stat}>
            <div className={s.statVal}>{(last['Ecosystem Level'] ?? 0).toFixed(1)}</div>
            <div className={s.statLabel}>{t('ending.stats.eco')}</div>
          </div>
        </div>

        <button className={s.compareBtn} onClick={onCompare}>
          {t('ending.compare')}
        </button>

        <button className={s.restartBtn} onClick={onRestart}>
          {t('ending.restart')}
        </button>
      </div>
    </div>
  )
}
