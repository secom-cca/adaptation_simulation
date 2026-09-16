import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { buildYearSnapshots, round1 } from '../data/resultScores.js'
import s from './ResultComparisonPage.module.css'

const API = import.meta.env.VITE_API_BASE || '/api'
const METRICS = [
  { key: 'flood', label: '洪水被害', value: 'floodDamageJpy', unit: '25年累計' },
  { key: 'crop', label: '農作物生産高', value: 'cropYield', unit: '25年平均' },
  { key: 'eco', label: '生態系', value: 'ecosystemLevel', unit: '25年平均' },
]
function objectValue(value) {
  if (value && typeof value === 'object') return value
  try { return JSON.parse(String(value).replaceAll("'", '"')) } catch { return {} }
}
function rawValue(metric, value) {
  const number = Number(value) || 0
  if (metric === 'flood') return `${Math.round(number).toLocaleString()} 円`
  return round1(number).toLocaleString()
}

export default function ResultComparisonPage({ sim, onBack }) {
  const { t } = useTranslation()
  const { history = [], currentClimateHistory = [], userName } = sim.gameState
  const [metric, setMetric] = useState('flood')
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const snapshots = useMemo(() => buildYearSnapshots(history, currentClimateHistory), [history, currentClimateHistory])
  const own = { name: userName || 'Guest', snapshots, isPlayer: true }

  useEffect(() => {
    let cancelled = false
    fetch(`${API}/comparison-results`).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(rows => {
      if (!cancelled) setGroups(rows.map(row => ({ name: row.user_name || 'Group', snapshots: [2050, 2075, 2100].map(year => ({ year, metrics: objectValue(row[`metrics_${year}`]) })) })))
    }).catch(() => !cancelled && setError(true)).finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  const participants = useMemo(() => [...groups.filter(x => x.name !== own.name), own], [groups, own.name, snapshots])
  const selected = METRICS.find(x => x.key === metric)
  return <div className={s.page}><div className={s.content}>
    <div className={s.header}><div><div className={s.kicker}>RESULTS</div><h1>参加者結果</h1><p>参加者ごとの実際のシミュレーション値を期間別に表示します。ゲーム本体は全員RCP4.5固定です。</p></div><button className={s.backBtn} onClick={onBack}>{t('comparison.back')}</button></div>
    <div className={s.tableCard}><div className={s.sectionTitle}>表示する指標</div><div className={s.metricTabs}>{METRICS.map(x => <button key={x.key} className={metric === x.key ? s.metricTabActive : s.metricTab} onClick={() => setMetric(x.key)}>{x.label}</button>)}</div></div>
    {loading && <div className={s.notice}>{t('comparison.loading')}</div>}{error && <div className={s.notice}>{t('comparison.error')}</div>}
    <div className={s.groupCard}><div className={s.sectionTitle}>{selected.label}（{selected.unit}）</div>
      <div className={s.participantTable}>
        <div className={s.participantHeader}><span>参加者</span><span>2050</span><span>2075</span><span>2100</span></div>
        {participants.map((row, index) => <div className={`${s.participantRow} ${row.isPlayer ? s.player : ''}`} key={`${row.name}-${index}`}><strong>{row.name}</strong>
          {[2050, 2075, 2100].map(year => { const snap = row.snapshots?.find(x => Number(x.year) === year); return <span key={year}>{rawValue(metric, snap?.metrics?.[selected.value])}</span> })}
        </div>)}
      </div>
    </div>
  </div></div>
}
