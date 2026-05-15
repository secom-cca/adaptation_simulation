import React, { useEffect, useMemo, useRef } from 'react'
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { POLICY_MANA_RULES } from '../data/budget.js'
import {
  BENCHMARK_SERIES,
  benchmarkSnapshots,
  benchmarkSummary,
  buildYearSnapshots,
  finalScores,
  round1,
} from '../data/resultScores.js'
import s from './EndingPage.module.css'

const API = '/api'

const POLICY_ORDER = [
  'planting_trees_amount',
  'house_migration_amount',
  'dam_levee_construction_cost',
  'paddy_dam_construction_cost',
  'capacity_building_cost',
  'agricultural_RnD_cost',
]

function formatFloodDamage(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `${(amount / 100_000_000).toFixed(1)}億円`
  if (amount >= 10_000) return `${Math.round(amount / 10_000).toLocaleString()}万円`
  return `${Math.round(amount).toLocaleString()}円`
}

function formatScore(value) {
  return round1(value).toFixed(1)
}

function radarData({ userScores, baselineScores = null, aiScores = null }) {
  return [
    {
      metric: '洪水被害',
      userScore: round1(userScores.floodScore),
      baselineScore: baselineScores ? round1(baselineScores.floodScore) : null,
      aiScore: aiScores ? round1(aiScores.floodScore) : null,
    },
    {
      metric: '農作物',
      userScore: round1(userScores.cropScore),
      baselineScore: baselineScores ? round1(baselineScores.cropScore) : null,
      aiScore: aiScores ? round1(aiScores.cropScore) : null,
    },
    {
      metric: '生態系',
      userScore: round1(userScores.ecosystemScore),
      baselineScore: baselineScores ? round1(baselineScores.ecosystemScore) : null,
      aiScore: aiScores ? round1(aiScores.ecosystemScore) : null,
    },
  ]
}

function ResultRadar({
  title,
  userSnapshot,
  baselineSnapshot = null,
  aiSnapshot = null,
  large = false,
}) {
  const data = radarData({
    userScores: userSnapshot.scores,
    baselineScores: baselineSnapshot?.scores ?? null,
    aiScores: aiSnapshot?.scores ?? null,
  })

  return (
    <div className={`${s.radarCard} ${large ? s.radarLarge : ''}`}>
      <div className={s.radarTitle}>{title}</div>
      <ResponsiveContainer width="100%" height={large ? 340 : 210}>
        <RadarChart
          data={data}
          outerRadius={large ? 112 : 72}
        >
          <PolarGrid />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fontSize: large ? 13 : 11, fill: '#38444c' }}
          />

          <Radar
            name="あなたの結果"
            dataKey="userScore"
            stroke="#3d6b8f"
            fill="#3d6b8f"
            fillOpacity={0.28}
          />

          {baselineSnapshot && (
            <Radar
              name="ベースライン"
              dataKey="baselineScore"
              stroke="#9b6b3f"
              fill="#9b6b3f"
              fillOpacity={0.12}
            />
          )}

          {aiSnapshot && (
            <Radar
              name="AIエージェント最適解"
              dataKey="aiScore"
              stroke="#4a8c5c"
              fill="#4a8c5c"
              fillOpacity={0.16}
            />
          )}

          {large && <Legend wrapperStyle={{ fontSize: 12 }} />}
        </RadarChart>
      </ResponsiveContainer>

      <div className={s.scoreLine}>
        あなたの総合スコア {formatScore(userSnapshot.scores.totalScore)}点
      </div>

      {large && baselineSnapshot && aiSnapshot && (
        <div className={s.scoreLine}>
          ベースライン {formatScore(baselineSnapshot.scores.totalScore)}点 / AI最適解 {formatScore(aiSnapshot.scores.totalScore)}点
        </div>
      )}
    </div>
  )
}

function ScoreComparisonCard({ title, subtitle, summary, snapshots, policies = null }) {
  const snapshot2050 = snapshots.find(snap => snap.year === 2050) ?? snapshots[0]
  const snapshot2075 = snapshots.find(snap => snap.year === 2075) ?? snapshots[1]
  const snapshot2100 = snapshots.find(snap => snap.year === 2100) ?? snapshots[snapshots.length - 1]

  return (
    <div className={s.comparisonCard}>
      <div className={s.comparisonHeader}>
        <div>
          <div className={s.comparisonTitle}>{title}</div>
          {subtitle && <div className={s.comparisonSub}>{subtitle}</div>}
        </div>
        <div className={s.comparisonScore}>{formatScore(summary.totalScore)}点</div>
      </div>

      <div className={s.comparisonGrid}>
        <div>
          <strong>洪水</strong>
          <span>{formatScore(summary.floodScore)}点</span>
        </div>
        <div>
          <strong>農作物</strong>
          <span>{formatScore(summary.cropScore)}点</span>
        </div>
        <div>
          <strong>生態系</strong>
          <span>{formatScore(summary.ecosystemScore)}点</span>
        </div>
      </div>

      <div className={s.comparisonYears}>
        <div>
          <strong>2050</strong>
          <span>{formatScore(snapshot2050.scores.totalScore)}点</span>
        </div>
        <div>
          <strong>2075</strong>
          <span>{formatScore(snapshot2075.scores.totalScore)}点</span>
        </div>
        <div>
          <strong>2100</strong>
          <span>{formatScore(snapshot2100.scores.totalScore)}点</span>
        </div>
      </div>

      <div className={s.comparisonMetrics}>
        <div>
          <strong>2100年 洪水被害</strong>
          <span>{formatFloodDamage(snapshot2100.metrics.floodDamageJpy)}</span>
        </div>
        <div>
          <strong>2100年 農作物</strong>
          <span>{Math.round(snapshot2100.metrics.cropYield).toLocaleString()}</span>
        </div>
        <div>
          <strong>2100年 生態系</strong>
          <span>{round1(snapshot2100.metrics.ecosystemLevel).toFixed(1)}</span>
        </div>
      </div>

      {policies && policies.length > 0 && (
        <div className={s.comparisonPolicies}>
          {policies.map(item => {
            const [label, ...rest] = item.split(':')
            return (
              <div key={item} className={s.policyRow}>
                <strong>{label}</strong>
                <span>{rest.join(':').trim()}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function summarizePolicies(policyHistory = []) {
  return policyHistory.slice(0, 3).map((entry, index) => ({
    label: `第${index + 1}ターン`,
    values: POLICY_ORDER.map(key => ({
      key,
      label: POLICY_MANA_RULES[key]?.labelJa || key,
      points: Math.round(Number(entry?.sliders?.[key]) || 0),
    })).filter(item => item.points > 0),
  }))
}

function buildComparisonPayload({ userName, mode, history, policyHistory }) {
  const snapshots = buildYearSnapshots(history)
  const final = finalScores(history)

  const payload = {
    user_name: userName || 'Guest',
    mode,
    total_score: round1(final.totalScore),
    flood_damage_score: round1(final.floodScore),
    crop_production_score: round1(final.cropScore),
    ecosystem_score: round1(final.ecosystemScore),
    timestamp: new Date().toISOString(),
  }

  snapshots.forEach(snapshot => {
    payload[`metrics_${snapshot.year}`] = snapshot.metrics
    payload[`scores_${snapshot.year}`] = {
      flood_damage_score: round1(snapshot.scores.floodScore),
      crop_production_score: round1(snapshot.scores.cropScore),
      ecosystem_score: round1(snapshot.scores.ecosystemScore),
      total_score: round1(snapshot.scores.totalScore),
    }
  })

  policyHistory.slice(0, 3).forEach((entry, index) => {
    payload[`turn_${index + 1}_policy_points`] = POLICY_ORDER.reduce((acc, key) => {
      acc[key] = Math.round(Number(entry?.sliders?.[key]) || 0)
      return acc
    }, {})
  })

  return payload
}

export default function EndingPage({ sim, onRestart, onCompare }) {
  const { t } = useTranslation()
  const { history, userName, mode, policyHistory = [] } = sim.gameState
  const savedComparisonRef = useRef(false)

  const snapshots = useMemo(() => buildYearSnapshots(history), [history])
  const userSummary = useMemo(() => finalScores(history), [history])

  const snapshot2050 = snapshots.find(snap => snap.year === 2050) ?? snapshots[0]
  const snapshot2075 = snapshots.find(snap => snap.year === 2075) ?? snapshots[1]
  const snapshot2100 = snapshots.find(snap => snap.year === 2100) ?? snapshots[snapshots.length - 1]

  const baselineSnapshots = useMemo(() => benchmarkSnapshots('baseline'), [])
  const aiSnapshots = useMemo(() => benchmarkSnapshots('aiOptimal'), [])
  const baselineSummary = useMemo(() => benchmarkSummary('baseline'), [])
  const aiSummary = useMemo(() => benchmarkSummary('aiOptimal'), [])

  const baselineSnapshot2050 = baselineSnapshots.find(snap => snap.year === 2050) ?? baselineSnapshots[0]
  const baselineSnapshot2075 = baselineSnapshots.find(snap => snap.year === 2075) ?? baselineSnapshots[1]
  const baselineSnapshot2100 = baselineSnapshots.find(snap => snap.year === 2100) ?? baselineSnapshots[baselineSnapshots.length - 1]

  const aiSnapshot2050 = aiSnapshots.find(snap => snap.year === 2050) ?? aiSnapshots[0]
  const aiSnapshot2075 = aiSnapshots.find(snap => snap.year === 2075) ?? aiSnapshots[1]
  const aiSnapshot2100 = aiSnapshots.find(snap => snap.year === 2100) ?? aiSnapshots[aiSnapshots.length - 1]

  const policies = useMemo(() => summarizePolicies(policyHistory), [policyHistory])
  const headline = t('ending.headline').replace('{name}', userName || 'Guest')

  useEffect(() => {
    if (!history.length || savedComparisonRef.current) return

    savedComparisonRef.current = true

    fetch(`${API}/comparison-results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildComparisonPayload({ userName, mode, history, policyHistory })),
    }).catch(() => {})
  }, [history, mode, policyHistory, userName])

  if (!snapshot2100) {
    return (
      <div className={s.page}>
        <div className={s.content}>
          <h1 className={s.headline}>結果を集計しています</h1>
        </div>
      </div>
    )
  }

  return (
    <div className={s.page}>
      <div className={s.content}>
        <div className={s.yearTag}>2100年 最終結果</div>
        <h1 className={s.headline}>{headline}</h1>

        <ResultRadar
          title="2100年：あなたの結果・ベースライン・AI最適解"
          userSnapshot={snapshot2100}
          baselineSnapshot={baselineSnapshot2100}
          aiSnapshot={aiSnapshot2100}
          large
        />

        <div className={s.aiPlan}>
          <div className={s.policyTitle}>AIエージェントの最適回答</div>
          {(BENCHMARK_SERIES.aiOptimal.policiesJa ?? []).map(item => {
            const [label, ...rest] = item.split(':')
            return (
              <div key={item} className={s.policyRow}>
                <strong>{label}</strong>
                <span>{rest.join(':').trim()}</span>
              </div>
            )
          })}
        </div>

        <div className={s.smallRadars}>
          <ResultRadar
            title="2050年"
            userSnapshot={snapshot2050}
            baselineSnapshot={baselineSnapshot2050}
            aiSnapshot={aiSnapshot2050}
          />
          <ResultRadar
            title="2075年"
            userSnapshot={snapshot2075}
            baselineSnapshot={baselineSnapshot2075}
            aiSnapshot={aiSnapshot2075}
          />
        </div>

        <div className={s.stats}>
          <div className={s.stat}>
            <div className={s.statVal}>
              {formatFloodDamage(snapshot2100.metrics.floodDamageJpy)}
              <small>（{formatScore(snapshot2100.scores.floodScore)}点）</small>
            </div>
            <div className={s.statLabel}>{t('ending.stats.flood')}</div>
          </div>

          <div className={s.stat}>
            <div className={s.statVal}>
              {Math.round(snapshot2100.metrics.cropYield).toLocaleString()}
              <small>（{formatScore(snapshot2100.scores.cropScore)}点）</small>
            </div>
            <div className={s.statLabel}>{t('ending.stats.yield')}</div>
          </div>

          <div className={s.stat}>
            <div className={s.statVal}>
              {round1(snapshot2100.metrics.ecosystemLevel).toFixed(1)}
              <small>（{formatScore(snapshot2100.scores.ecosystemScore)}点）</small>
            </div>
            <div className={s.statLabel}>{t('ending.stats.eco')}</div>
          </div>
        </div>

        <div className={s.resultComparison}>
          <div className={s.policyTitle}>結果比較</div>

          <ScoreComparisonCard
            title="あなたの結果"
            subtitle="実際に選んだ政策配分による結果"
            summary={userSummary}
            snapshots={snapshots}
          />
        </div>

        <div className={s.policySummary}>
          <div className={s.policyTitle}>政策配分の概要</div>
          {policies.map(turn => (
            <div key={turn.label} className={s.policyRow}>
              <strong>{turn.label}</strong>
              <span>
                {turn.values.length
                  ? turn.values.map(item => `${item.label} ${item.points}ポイント`).join(' / ')
                  : '投資なし'}
              </span>
            </div>
          ))}
        </div>

        <button className={s.compareBtn} onClick={onCompare}>{t('ending.compare')}</button>
        <button className={s.restartBtn} onClick={onRestart}>{t('ending.restart')}</button>
      </div>
    </div>
  )
}