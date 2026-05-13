import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './ResultComparisonPage.module.css'

const API = '/api'

const BASELINE_SUMMARY = {
  flood: 4_360_000_000,
  yield: 1628,
  eco: 71.6,
  burden: 6055,
}

const METRICS = [
  { key: 'flood', labelKey: 'comparison.flood', lowerIsBetter: true },
  { key: 'yield', labelKey: 'comparison.yield', lowerIsBetter: false },
  { key: 'eco', labelKey: 'comparison.eco', lowerIsBetter: false },
  { key: 'burden', labelKey: 'comparison.burden', lowerIsBetter: true },
]

function sum(rows, key) {
  return rows.reduce((total, row) => total + (Number(row?.[key]) || 0), 0)
}

function floodJpy(row) {
  return Number(row?.['Flood Damage JPY'] ?? ((row?.['Flood Damage'] ?? 0) * 150)) || 0
}

function avg(rows, key) {
  return rows.length ? sum(rows, key) / rows.length : 0
}

function summarizeRows(rows = {}) {
  const list = Array.isArray(rows) ? rows : []
  const last = list[list.length - 1] ?? {}
  return {
    flood: list.reduce((total, row) => total + floodJpy(row), 0),
    yield: Number(last['Crop Yield']) || avg(list, 'Crop Yield'),
    eco: Number(last['Ecosystem Level']) || avg(list, 'Ecosystem Level'),
    burden: avg(list, 'Resident Burden'),
  }
}

function formatValue(metric, value) {
  if (value == null) return '-'
  const numeric = Number(value) || 0
  if (metric === 'flood') {
    if (numeric >= 100_000_000) return `${(numeric / 100_000_000).toFixed(1)}億円`
    if (numeric >= 10_000) return `${Math.round(numeric / 10_000).toLocaleString()}万円`
    return `${Math.round(numeric).toLocaleString()}円`
  }
  if (metric === 'eco') return numeric.toFixed(1)
  return String(Math.round(numeric))
}

function compareClass(player, baseline, metric) {
  if (!baseline || baseline[metric.key] == null) return ''
  const p = Number(player?.[metric.key]) || 0
  const b = Number(baseline?.[metric.key]) || 0
  if (p === b) return ''
  const better = metric.lowerIsBetter ? p < b : p > b
  return better ? s.good : s.bad
}

function summarizeOtherGroups(rows = []) {
  return rows
    .map(row => ({
      name: row.user_name || 'Group',
      averageScore: Number(row.total_score) || 0,
      values: {
        flood: Number(row.cumulative_flood_damage) || 0,
        yield: Number(row.final_crop_yield) || 0,
        eco: Number(row.final_ecosystem_level) || 0,
        burden: Number(row.average_resident_burden) || 0,
      },
    }))
    .sort((a, b) => b.averageScore - a.averageScore)
    .slice(0, 8)
}

export default function ResultComparisonPage({ sim, onBack }) {
  const { t } = useTranslation()
  const { history } = sim.gameState
  const playerSummary = useMemo(() => summarizeRows(history), [history])
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    fetch(`${API}/comparison-results`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        if (cancelled) return
        setGroups(summarizeOtherGroups(data))
      })
      .catch(() => {
        if (!cancelled) setError('partial')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const baselineSummary = BASELINE_SUMMARY
  const comparisonRows = [
    { id: 'player', label: t('comparison.yourResult'), values: playerSummary, className: s.player },
    { id: 'baseline', label: t('comparison.baseline'), values: baselineSummary ?? {}, className: s.baseline },
  ]

  return (
    <div className={s.page}>
      <div className={s.content}>
        <div className={s.header}>
          <div>
            <div className={s.kicker}>{t('comparison.kicker')}</div>
            <h1>{t('comparison.title')}</h1>
            <p>{t('comparison.description')}</p>
          </div>
          <button className={s.backBtn} onClick={onBack}>{t('comparison.back')}</button>
        </div>

        {loading && <div className={s.notice}>{t('comparison.loading')}</div>}
        {error && <div className={s.notice}>{t('comparison.error')}</div>}

        <div className={s.tableCard}>
          <div className={s.tableHeader}>
            <span>{t('comparison.scenario')}</span>
            {METRICS.map(metric => <span key={metric.key}>{t(metric.labelKey)}</span>)}
          </div>
          {comparisonRows.map(row => (
            <div key={row.id} className={`${s.tableRow} ${row.className}`}>
              <strong>{row.label}</strong>
              {METRICS.map(metric => (
                <span key={metric.key} className={row.id === 'player' ? compareClass(row.values, baselineSummary, metric) : ''}>
                  {formatValue(metric.key, row.values[metric.key])}
                </span>
              ))}
            </div>
          ))}
        </div>

        <div className={s.groupCard}>
          <div className={s.sectionTitle}>{t('comparison.groups')}</div>
          {groups.length === 0 ? (
            <p className={s.empty}>{t('comparison.noGroups')}</p>
          ) : (
            <div className={s.groupList}>
              {groups.map((group, index) => (
                <div key={group.name} className={s.groupRow}>
                  <span className={s.groupRank}>{index + 1}</span>
                  <div className={s.groupInfo}>
                    <div className={s.groupTop}>
                      <strong>{group.name}</strong>
                      <span>{group.averageScore.toFixed(1)}</span>
                    </div>
                    <div className={s.metricList}>
                      {METRICS.map(metric => (
                        <div key={metric.key} className={s.metricItem}>
                          <span>{t(metric.labelKey)}</span>
                          <strong>{formatValue(metric.key, group.values[metric.key])}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
