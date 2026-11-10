import React, { useMemo } from 'react'
import { POLICY_MANA_RULES, POLICY_POINT_KEYS } from '../data/budget.js'
import s from './DecisionPathwayPage.module.css'

const POLICY_COLORS = {
  planting_trees_amount: '#2f7d62',
  house_migration_amount: '#d26a4a',
  dam_levee_construction_cost: '#3478a8',
  paddy_dam_construction_cost: '#37a6a0',
  agricultural_RnD_cost: '#d19b32',
  capacity_building_cost: '#8065ad',
}

const MAP = {
  width: 1120,
  height: 610,
  labelX: 34,
  lineStart: 300,
  lineEnd: 990,
  yearX: [300, 530, 760, 990],
  firstLaneY: 206,
  laneGap: 66,
}

function pointValue(entry, key) {
  return Math.max(0, Math.round(Number(entry?.sliders?.[key]) || 0))
}

function periodLabel(entry, index) {
  const start = Number(entry?.year)
  const fallback = 2026 + index * 25
  const year = Number.isFinite(start) ? start : fallback
  return `${year}–${year + 24}`
}

export default function DecisionPathwayMap({ policyHistory = [], userName = 'Guest' }) {
  const turns = useMemo(() => Array.from({ length: 3 }, (_, index) => policyHistory[index] ?? null), [policyHistory])
  const turnTotals = useMemo(
    () => turns.map(entry => POLICY_POINT_KEYS.reduce((sum, key) => sum + pointValue(entry, key), 0)),
    [turns],
  )
  const policyTotals = useMemo(
    () => POLICY_POINT_KEYS.map(key => turns.reduce((sum, entry) => sum + pointValue(entry, key), 0)),
    [turns],
  )

  return (
    <div className={s.embedded}>
        <section className={s.mapCard}>
          <div className={s.mapHeading}>
            <div><span>DECISION PATHWAYS · 2026–2100</span><h2>{userName || 'Guest'}さんの意思決定メトロマップ</h2></div>
          </div>
          <div className={s.mapScroller} tabIndex="0" aria-label="政策経路図。横方向にスクロールできます">
            <svg className={s.map} viewBox={`0 0 ${MAP.width} ${MAP.height}`} role="img" aria-labelledby="pathway-title pathway-desc">
              <title id="pathway-title">2026年から2100年までの政策投資メトロマップ</title>
              <desc id="pathway-desc">6つの政策分野について、各期間の投資ポイントを路線の太さとして示しています。</desc>

              <text x={MAP.labelX} y="54" className={s.svgCaption}>政策分野 / 路線</text>
              <text x="1102" y="54" textAnchor="end" className={s.svgCaption}>期間合計</text>
              <line x1={MAP.lineStart} y1="76" x2={MAP.lineEnd} y2="76" className={s.timeline} />

              {MAP.yearX.map((x, index) => {
                const yearLabels = ['2026', '2051', '2076', '2100']
                return (
                  <g key={index}>
                    <line x1={x} y1="76" x2={x} y2="570" className={s.turnGuide} />
                    <circle cx={x} cy="76" r="8" className={s.timelineStation} />
                    <text x={x} y="51" textAnchor="middle" className={s.yearLabel}>{yearLabels[index]}</text>
                  </g>
                )
              })}

              {turns.map((entry, index) => {
                const x = (MAP.yearX[index] + MAP.yearX[index + 1]) / 2
                return (
                  <g key={index}>
                    <text x={x} y="108" textAnchor="middle" className={s.periodTitle}>{periodLabel(entry, index)}</text>
                    <rect x={x - 54} y="118" width="108" height="34" rx="17" className={s.turnTotalPill} />
                    <text x={x} y="140" textAnchor="middle" className={s.turnTotalText}>合計 {turnTotals[index]} pt</text>
                  </g>
                )
              })}

              {POLICY_POINT_KEYS.map((key, policyIndex) => {
                const y = MAP.firstLaneY + policyIndex * MAP.laneGap
                const color = POLICY_COLORS[key]
                const total = policyTotals[policyIndex]
                return (
                  <g key={key}>
                    <line x1={MAP.lineStart} y1={y} x2={MAP.lineEnd} y2={y} className={s.routeBase} />
                    <text x={MAP.labelX} y={y - 5} className={s.policyLabel}>{POLICY_MANA_RULES[key]?.labelJa || key}</text>
                    <text x={MAP.labelX} y={y + 17} className={s.policyDescription}>{POLICY_MANA_RULES[key]?.summaryJa}</text>
                    <rect x="1016" y={y - 18} width="86" height="36" rx="18" fill={color} className={s.policyTotalPill} />
                    <text x="1059" y={y + 6} textAnchor="middle" className={s.policyTotalText}>{total} pt</text>

                    {turns.map((entry, turnIndex) => {
                      const points = pointValue(entry, key)
                      const x1 = MAP.yearX[turnIndex]
                      const x2 = MAP.yearX[turnIndex + 1]
                      const centerX = (x1 + x2) / 2
                      const active = points > 0
                      return (
                        <g key={turnIndex}>
                          <line
                            x1={x1 + 9}
                            y1={y}
                            x2={x2 - 9}
                            y2={y}
                            stroke={active ? color : '#cbd3d8'}
                            strokeWidth={active ? 4 + Math.min(points, 10) * 2.2 : 3}
                            className={active ? s.investmentEdge : s.emptyEdge}
                          />
                          <rect x={centerX - 19} y={y - 13} width="38" height="26" rx="13" fill="white" stroke={active ? color : '#b7c0c6'} className={s.edgeLabelPill} />
                          <text x={centerX} y={y + 5} textAnchor="middle" fill={active ? color : '#8a969e'} className={s.edgeLabel}>{points} pt</text>
                        </g>
                      )
                    })}
                    {MAP.yearX.map((x, index) => (
                      <circle key={index} cx={x} cy={y} r="7" fill="white" stroke={color} className={s.fixedStation} />
                    ))}
                  </g>
                )
              })}
            </svg>
          </div>
        </section>
    </div>
  )
}
