import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { buildYearSnapshots, round1 } from '../data/resultScores.js'
import s from './ResultComparisonPage.module.css'

const API = import.meta.env.VITE_API_BASE || '/api'
const METRICS = [
  { key: 'flood', label: '洪水被害', value: 'floodDamageJpy', unit: '25年累計', lowerIsBetter: true },
  { key: 'crop', label: '農作物生産高', value: 'cropYield', unit: '25年平均', lowerIsBetter: false },
  { key: 'eco', label: '生態系', value: 'ecosystemLevel', unit: '25年平均', lowerIsBetter: false },
]
function objectValue(value) {
  if (value && typeof value === 'object') return value
  try { return JSON.parse(String(value).replaceAll("'", '"')) } catch { return {} }
}
function displayValue(metric, value) {
  const number = Number(value) || 0
  return metric.key === 'flood' ? `${Math.round(number).toLocaleString()} 円` : round1(number).toLocaleString()
}

export default function ResultComparisonPage({ sim, onBack }) {
  const { t } = useTranslation()
  const { history = [], currentClimateHistory = [], userName, rcpValue } = sim.gameState
  const [sort, setSort] = useState({ key: 'flood', direction: 'asc' })
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const scenarioId = String(rcpValue)
  const scenarioLabel = rcpValue === 'composite' ? '複合シナリオ' : `RCP${rcpValue}`
  const snapshots = useMemo(() => buildYearSnapshots(history, currentClimateHistory), [history, currentClimateHistory])
  const own = { name: userName || 'Guest', metrics: snapshots.find(x => Number(x.year) === 2100)?.metrics ?? {}, isPlayer: true }

  useEffect(() => {
    let cancelled = false
    fetch(`${API}/comparison-results`).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(rows => {
      if (!cancelled) setGroups(rows.filter(row => String(row.rcp_scenario ?? '4.5') === scenarioId).map(row => ({ name: row.user_name || 'Group', metrics: objectValue(row.metrics_2100) })))
    }).catch(() => !cancelled && setError(true)).finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [scenarioId])

  const participants = useMemo(() => {
    const rows = [...groups.filter(row => row.name !== own.name), own]
    const metric = METRICS.find(item => item.key === sort.key) ?? METRICS[0]
    rows.sort((a, b) => {
      const av = Number(a.metrics?.[metric.value]) || 0
      const bv = Number(b.metrics?.[metric.value]) || 0
      return sort.direction === 'asc' ? av - bv : bv - av
    })
    return rows.map((row, index) => ({ ...row, rank: index + 1 }))
  }, [groups, own.name, snapshots, sort])

  function changeSort(metric) {
    setSort(previous => previous.key === metric.key
      ? { key: metric.key, direction: previous.direction === 'asc' ? 'desc' : 'asc' }
      : { key: metric.key, direction: metric.lowerIsBetter ? 'asc' : 'desc' })
  }

  function sortMark(metric) {
    if (sort.key !== metric.key) return '↕'
    return sort.direction === 'asc' ? '↑' : '↓'
  }

  return <div className={s.page}><div className={s.content}>
    <div className={s.header}><div><div className={s.kicker}>RESULTS</div><h1>参加者結果</h1><p>{scenarioLabel}を選んだ参加者だけを対象に、2100年の3項目を一覧表示します。項目名を押すと、その項目の順位に並び替わります。</p></div><button className={s.backBtn} onClick={onBack}>{t('comparison.back')}</button></div>
    {loading && <div className={s.notice}>{t('comparison.loading')}</div>}{error && <div className={s.notice}>{t('comparison.error')}</div>}
    <div className={s.groupCard}><div className={s.sectionTitle}>2100年の結果</div><div className={s.participantTable}>
      <div className={s.participantHeader}><span>参加者</span><span>順位</span>{METRICS.map(metric => <button key={metric.key} type="button" className={sort.key === metric.key ? s.sortActive : s.sortButton} onClick={() => changeSort(metric)}>{metric.label}<small>{metric.unit}</small><b>{sortMark(metric)}</b></button>)}</div>
      {participants.map(row => <div className={`${s.participantRow} ${row.isPlayer ? s.player : ''}`} key={row.name}><strong>{row.name} <small>（{row.rank}位）</small></strong><span>{row.rank}位</span>{METRICS.map(metric => <span key={metric.key}>{displayValue(metric, row.metrics?.[metric.value])}</span>)}</div>)}
    </div></div>
  </div></div>
}
