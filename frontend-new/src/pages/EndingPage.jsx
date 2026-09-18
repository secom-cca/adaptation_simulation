import React, { useEffect, useMemo, useRef } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { POLICY_MANA_RULES } from '../data/budget.js'
import { buildYearSnapshots, finalScores, round1 } from '../data/resultScores.js'
import s from './EndingPage.module.css'

const API = import.meta.env.VITE_API_BASE || '/api'
const POLICY_ORDER = ['planting_trees_amount', 'house_migration_amount', 'dam_levee_construction_cost', 'paddy_dam_construction_cost', 'capacity_building_cost', 'agricultural_RnD_cost']
const METRICS = [
  { key: 'flood', title: '洪水被害', score: 'floodScore', value: 'floodDamageJpy', unit: '円（期間累計）' },
  { key: 'crop', title: '農作物生産高', score: 'cropScore', value: 'cropYield', unit: '期間平均' },
  { key: 'eco', title: '生態系', score: 'ecosystemScore', value: 'ecosystemLevel', unit: '期間平均' },
]

function fmtValue(metric, value) {
  const n = Number(value) || 0
  return metric.key === 'flood' ? `${Math.round(n).toLocaleString()} 円` : round1(n).toLocaleString()
}
function policiesForDisplay(history = []) {
  return history.slice(0, 3).map((entry, index) => ({
    turn: `第${index + 1}ターン`,
    text: POLICY_ORDER.map(key => ({ label: POLICY_MANA_RULES[key]?.labelJa || key, points: Math.round(Number(entry?.sliders?.[key]) || 0) }))
      .filter(item => item.points > 0).map(item => `${item.label} ${item.points}点`).join(' / ') || '投資なし',
  }))
}
function comparisonPayload({ userName, mode, rcpValue, history, currentClimateHistory, policyHistory }) {
  const snapshots = buildYearSnapshots(history, currentClimateHistory)
  const summary = finalScores(history, currentClimateHistory)
  const payload = { user_name: userName || 'Guest', mode, rcp_scenario: String(rcpValue), total_score: round1(summary.totalScore), flood_damage_score: round1(summary.floodScore), crop_production_score: round1(summary.cropScore), ecosystem_score: round1(summary.ecosystemScore) }
  snapshots.forEach(x => { payload[`metrics_${x.year}`] = x.metrics; payload[`scores_${x.year}`] = { flood_damage_score: round1(x.scores.floodScore), crop_production_score: round1(x.scores.cropScore), ecosystem_score: round1(x.scores.ecosystemScore), total_score: round1(x.scores.totalScore) } })
  policyHistory.slice(0, 3).forEach((entry, i) => { payload[`turn_${i + 1}_policy_points`] = entry.sliders || {} })
  return payload
}

function MetricSection({ metric, player, rcp, scenarioLabel }) {
  const data = player.map((x, i) => ({ year: String(x.year), rcp: Number(rcp[i]?.metrics?.[metric.value]) || 0, player: Number(x.metrics[metric.value]) || 0 }))
  return <section className={`${s.metricSection} ${metric.key === 'flood' ? s.metricWide : ''}`}>
    <h2>{metric.title}</h2>
    <div className={s.chartPanel}><ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 14, right: 12, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="year" /><YAxis domain={[0, 'auto']} tickFormatter={v => metric.key === 'flood' ? `${Math.round(v / 1000000)}M` : v} />
        <Tooltip formatter={v => fmtValue(metric, v)} /><Legend />
        <Bar name={`${scenarioLabel}・無対策`} dataKey="rcp" fill="#a98a64" radius={[5, 5, 0, 0]} /><Bar name="あなたの政策" dataKey="player" fill="#3d6b8f" radius={[5, 5, 0, 0]} />
      </BarChart>
    </ResponsiveContainer></div>
    <div className={s.actualTable}>
      <div className={s.actualHeader}><strong>スコア（点）</strong>{player.map(x => <strong key={x.year}>{x.year}</strong>)}</div>
      {[[`${scenarioLabel}・無対策`, rcp], ['あなたの政策', player]].map(([label, rows]) => <div className={s.actualRow} key={label}><span>{label}</span>{rows.map(x => <span key={x.year}>{round1(x.scores[metric.score])}</span>)}</div>)}
    </div>
  </section>
}

export default function EndingPage({ sim, onCompare, onOpenSurvey, onRetryExport }) {
  const { t } = useTranslation()
  const { history = [], baselineHistory = [], currentClimateHistory = [], userName, mode, rcpValue, policyHistory = [], exportDone, exportError, exportFilename, surveySubmitted } = sim.gameState
  const scenarioLabel = rcpValue === 'composite' ? 'RCP4.5（複合）' : `RCP${rcpValue}`
  const saved = useRef(false)
  const player = useMemo(() => buildYearSnapshots(history, currentClimateHistory), [history, currentClimateHistory])
  const rcp = useMemo(() => buildYearSnapshots(baselineHistory, currentClimateHistory), [baselineHistory, currentClimateHistory])
  const policies = useMemo(() => policiesForDisplay(policyHistory), [policyHistory])
  useEffect(() => {
    if (!history.length || saved.current) return
    saved.current = true
    fetch(`${API}/comparison-results`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(comparisonPayload({ userName, mode, rcpValue, history, currentClimateHistory, policyHistory })) }).catch(() => {})
  }, [history, currentClimateHistory, mode, policyHistory, rcpValue, userName])
  return <div className={s.page}><div className={s.content}>
    <div className={s.yearTag}>2026–2100 最終結果</div><h1 className={s.headline}>{userName || 'Guest'}さんの適応結果</h1>
    <p className={s.methodNote}>各指標は「現在気候・無対策」を100点とした相対評価です。洪水被害は期間累計、農作物生産高と生態系は期間平均で評価します。100点を上限にはしていません。</p>
    <div className={s.metricsLayout}>{METRICS.map(metric => <MetricSection key={metric.key} metric={metric} player={player} rcp={rcp} scenarioLabel={scenarioLabel} />)}</div>
    <section className={s.policySummary}><div className={s.policyTitle}>政策履歴</div>{policies.map(x => <div className={s.policyRow} key={x.turn}><strong>{x.turn}</strong><span>{x.text}</span></div>)}</section>
    <button className={s.compareBtn} onClick={onCompare}>参加者結果を見る</button><button className={s.surveyBtn} onClick={onOpenSurvey} type="button">{surveySubmitted ? t('ending.survey.done') : t('ending.survey')}</button>
    {exportError && <button type="button" className={s.saveLogBtn} onClick={() => onRetryExport?.()}>{t('ending.export.retry')}</button>}{exportDone && !exportError && exportFilename && <p className={s.exportNote}>{t('ending.export.done')} ({exportFilename})</p>}
    <p className={s.exportNote}>{t('ending.export.hint')}</p>
  </div></div>
}
