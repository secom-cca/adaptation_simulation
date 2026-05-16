import React, { useEffect, useMemo, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import {
  BENCHMARK_SERIES,
  benchmarkSummary,
  buildYearSnapshots,
  finalScores,
  round1,
} from '../data/resultScores.js'
import s from './ResultComparisonPage.module.css'

const API = '/api'

const METRICS = [
  { key: 'total', label: '総合スコア' },
  { key: 'flood', label: '洪水被害' },
  { key: 'crop', label: '農作物生産' },
  { key: 'eco', label: '生態系' },
]

function summarizeRows(rows = []) {
  const scores = finalScores(rows)
  return {
    total: round1(scores.totalScore),
    flood: round1(scores.floodScore),
    crop: round1(scores.cropScore),
    eco: round1(scores.ecosystemScore),
  }
}

function summarizeOtherGroups(rows = []) {
  return rows
    .map(row => ({
      name: row.user_name || 'Group',
      values: {
        total: Number(row.total_score) || 0,
        flood: Number(row.flood_damage_score) || 0,
        crop: Number(row.crop_production_score) || 0,
        eco: Number(row.ecosystem_score) || 0,
      },
    }))
    .sort(compareRankRows)
}

function compareRankRows(a, b) {
  return (b.values.total - a.values.total)
    || (b.values.flood - a.values.flood)
    || (b.values.crop - a.values.crop)
    || (b.values.eco - a.values.eco)
}

function formatScore(value) {
  return `${round1(value).toFixed(1)}点`
}

export default function ResultComparisonPage({ sim, onBack }) {
  const { t } = useTranslation()
  const { history, userName } = sim.gameState
  const playerSummary = useMemo(() => summarizeRows(history), [history])
  const baselineSummary = useMemo(() => {
    const scores = benchmarkSummary('baseline')
    return {
      total: round1(scores.totalScore),
      flood: round1(scores.floodScore),
      crop: round1(scores.cropScore),
      eco: round1(scores.ecosystemScore),
    }
  }, [])
  const aiSummary = useMemo(() => {
    const scores = benchmarkSummary('aiOptimal')
    return {
      total: round1(scores.totalScore),
      flood: round1(scores.floodScore),
      crop: round1(scores.cropScore),
      eco: round1(scores.ecosystemScore),
    }
  }, [])
  const snapshots = useMemo(() => buildYearSnapshots(history), [history])
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
        if (!cancelled) setGroups(summarizeOtherGroups(data))
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

  const fullRanking = useMemo(() => {
    const others = groups.filter(group => group.name !== (userName || 'Guest'))
    return [...others, { name: userName || 'Guest', values: playerSummary, isPlayer: true }].sort(compareRankRows)
  }, [groups, playerSummary, userName])
  const playerRank = Math.max(1, fullRanking.findIndex(row => row.isPlayer) + 1)

  return (
    <div className={s.page}>
      <div className={s.content}>
        <div className={s.header}>
          <div>
            <div className={s.kicker}>{t('comparison.kicker')}</div>
            <h1>{t('comparison.title')}</h1>
            <p>総合スコアは洪水被害・農作物生産・生態系の3指標を0-100点に正規化し、単純平均しています。ベースライン（対策なし）の結果は比較用として残しています。</p>
          </div>
          <button className={s.backBtn} onClick={onBack}>{t('comparison.back')}</button>
        </div>

        {loading && <div className={s.notice}>{t('comparison.loading')}</div>}
        {error && <div className={s.notice}>{t('comparison.error')}</div>}

        <div className={s.summaryGrid}>
          <ScoreCard title={t('comparison.yourResult')} values={playerSummary} tone="player" />
          <ScoreCard title={BENCHMARK_SERIES.baseline.labelJa} values={baselineSummary} tone="baseline" />
          <ScoreCard title={BENCHMARK_SERIES.aiOptimal.labelJa} values={aiSummary} tone="optimal" />
        </div>

        <div className={s.tableCard}>
          <div className={s.sectionTitle}>スコア詳細</div>
          <div className={s.tableHeader}>
            <span>{t('comparison.scenario')}</span>
            {METRICS.map(metric => <span key={metric.key}>{metric.label}</span>)}
          </div>
          {[
            [t('comparison.yourResult'), playerSummary, s.player],
            [BENCHMARK_SERIES.baseline.labelJa, baselineSummary, s.baseline],
            [BENCHMARK_SERIES.aiOptimal.labelJa, aiSummary, s.optimal],
          ].map(([label, values, klass]) => (
            <div key={label} className={`${s.tableRow} ${klass}`}>
              <strong>{label}</strong>
              {METRICS.map(metric => <span key={metric.key}>{formatScore(values[metric.key])}</span>)}
            </div>
          ))}
        </div>

        <div className={s.tableCard}>
          <div className={s.sectionTitle}>あなたの順位</div>
          <p className={s.empty}>あなたの順位：{playerRank}位 / {fullRanking.length}人中　総合スコア：{formatScore(playerSummary.total)}</p>
        </div>

        <div className={s.groupCard}>
          <div className={s.sectionTitle}>参加者ランキング</div>
          {groups.length === 0 ? (
            <p className={s.empty}>{t('comparison.noGroups')}</p>
          ) : (
            <div className={s.groupList}>
              {groups.slice(0, 5).map((group, index) => (
                <div key={`${group.name}-${index}`} className={s.groupRow}>
                  <span className={s.groupRank}>{index + 1}</span>
                  <div className={s.groupInfo}>
                    <div className={s.groupTop}>
                      <strong>{group.name}</strong>
                      <span>{formatScore(group.values.total)}</span>
                    </div>
                    <div className={s.metricList}>
                      {METRICS.slice(1).map(metric => (
                        <div key={metric.key} className={s.metricItem}>
                          <span>{metric.label}</span>
                          <strong>{formatScore(group.values[metric.key])}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={s.tableCard}>
          <div className={s.sectionTitle}>年別スコア</div>
          <div className={s.metricList}>
            {snapshots.map(snapshot => (
              <div key={snapshot.year} className={s.metricItem}>
                <span>{snapshot.year}年</span>
                <strong>{formatScore(snapshot.scores.totalScore)}</strong>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ScoreCard({ title, values, tone }) {
  return (
    <div className={`${s.scoreCard} ${s[tone]}`}>
      <span>{title}</span>
      <strong>{formatScore(values.total)}</strong>
      <div>
        {METRICS.slice(1).map(metric => (
          <small key={metric.key}>{metric.label}: {formatScore(values[metric.key])}</small>
        ))}
      </div>
    </div>
  )
}
