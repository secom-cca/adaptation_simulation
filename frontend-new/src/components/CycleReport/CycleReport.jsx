import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { scoresForRow, round1 } from '../../data/resultScores.js'
import s from '../../pages/ConsequencePage.module.css'
import own from './CycleReport.module.css'
import { formatJpyInline, formatJpyShort, formatJpy } from '../../utils/formatJpy'



const REPORT_COLOR = '#5a6a7a'

const METRICS = [
  {
    key: 'floodScore',
    icon: '🌊',
    label: '洪水被害スコア',
    rawLabel: '25年累計',
    rawValue: summary => formatJpyShort(summary.floodDamageTotal),
    good: (v, p) => p != null && v > p,
  },
  {
    key: 'cropScore',
    icon: '🌾',
    label: '農作物生産スコア',
    rawLabel: '25年平均',
    rawValue: summary => fmtNumber(summary.cropYieldAvg, 1),
    good: (v, p) => p != null && v > p,
  },
  {
    key: 'ecosystemScore',
    icon: '🌿',
    label: '生態系スコア',
    rawLabel: '25年平均',
    rawValue: summary => fmtNumber(summary.ecosystemAvg, 1),
    good: (v, p) => p != null && v > p,
  },
]

function avg(rows, key) {
  if (!rows.length) return 0
  return rows.reduce((sum, r) => sum + (Number(r[key]) || 0), 0) / rows.length
}

function sum(rows, key) {
  return rows.reduce((total, r) => total + (Number(r[key]) || 0), 0)
}

function fmtNumber(value, digits = 0) {
  return Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  })
}

// format helpers moved to ../../utils/formatJpy

function summarizeCycleRows(rows = [], year) {
  const lastRow = rows[rows.length - 1] ?? {}

  const floodDamageTotal = sum(rows, 'Flood Damage JPY')
  const cropYieldAvg = avg(rows, 'Crop Yield')
  const ecosystemAvg = avg(rows, 'Ecosystem Level')

  return {
    floodDamageTotal,
    cropYieldAvg,
    ecosystemAvg,
    scoreRow: {
      ...lastRow,

      // サイクル代表値に差し替え
      // 洪水：25年累計
      // 農作物：25年平均
      // 生態系：25年平均
      'Flood Damage JPY': floodDamageTotal,
      'Crop Yield': cropYieldAvg,
      'Ecosystem Level': ecosystemAvg,

      year,
    },
  }
}

export default function CycleReport({ history, year, cycle, llmCommentary, llmLoading, onViewDetails }) {
  const { t } = useTranslation()
  const cycleStart = year - 25
  const cycleEnd = year - 1

  const thisRows = history.slice(-25)
  const prevRows = history.length > 25 ? history.slice(-50, -25) : []

  const cycleSummary = summarizeCycleRows(thisRows, cycleEnd)
  const prevSummary = prevRows.length ? summarizeCycleRows(prevRows, cycleStart - 1) : null

  const currentScores = scoresForRow(cycleSummary.scoreRow, cycleEnd)
  const prevScores = prevSummary ? scoresForRow(prevSummary.scoreRow, cycleStart - 1) : null

  return (
    <div className={s.page} style={{ '--event-color': REPORT_COLOR }}>
      <div className={`${s.card} ${own.reportCard}`}>
        <img className={`${s.eventImage} ${own.reportImage}`} src="/events/report.png" alt="cycle report" />
        <div className={`${s.content} ${own.reportContent}`}>
          <div className={s.meta}>
            <span className={s.yearTag}>{cycleStart} - {cycleEnd}</span>
            <span className={s.subtitle}>{t('report.subtitle').replace('{n}', cycle - 1)}</span>
          </div>
          <h1 className={s.title}>{t('report.title')}</h1>

          <div className={own.stats}>
            {METRICS.map(m => {
              const val = currentScores[m.key] ?? 0
              const prev = prevScores ? prevScores[m.key] : null
              const delta = prev != null ? val - prev : null
              const isGood = m.good(val, prev)

              return (
                <div key={m.key} className={own.stat}>
                  <span className={own.statIcon}>{m.icon}</span>
                  <span className={own.statLabel}>{m.label}</span>
                  <span className={own.statVal}>{round1(val).toFixed(1)}点</span>

                  {delta != null && (
                    <span className={`${own.statDelta} ${isGood ? own.good : own.bad}`}>
                      {delta > 0 ? '+' : ''}{round1(delta).toFixed(1)}
                    </span>
                  )}

                  <span className={own.statRaw}>
                    {m.rawLabel}: {m.rawValue(cycleSummary)}
                  </span>
                </div>
              )
            })}
          </div>

          <div className={own.reportActions}>
            <button className={s.continueBtn} onClick={onViewDetails}>{t('report.cta')}</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function collectCycleEvents(rows = []) {
  const events = []
  rows.forEach(row => {
    const backendEvents = Array.isArray(row.events) ? row.events : (Array.isArray(row.Events) ? row.Events : [])
    backendEvents.forEach(ev => {
      if (ev.category === 'urban') return
      events.push({
        year: ev.year ?? row.year,
        icon: eventIcon(ev.category),
        category: categoryLabel(ev.category),
        title: ev.title ?? 'イベント',
        body: eventBody(ev, row),
        severity: ev.severity === 'critical' ? 'critical' : ev.severity === 'success' ? 'ok' : 'warn',
      })
    })
  })
  return events
}

function eventBody(ev, row = {}) {
  if (ev.category === 'agriculture') {
    const maxRain = Number(row['Extreme Precip Events'] ?? row.max_rain_event ?? 0) || 0
    const floodDamage = Number(row['Flood Damage JPY'] ?? ((row['Flood Damage'] ?? 0) * 150)) || 0
    if (maxRain >= 160 || floodDamage > 0) {
      const rainText = maxRain >= 160 ? `この年は大雨が発生し、` : ''
      const damageText = floodDamage > 0 ? `洪水被害は${formatJpyInline(floodDamage)}でした。` : ''
      return `${rainText}${damageText} その影響で農作物生産が初期水準を下回っています。`
    }
  }
  const value = ev.metric?.includes('Damage') ? `${formatJpy(ev.value)} ` : ''
  return `${value}${ev.message ?? ''}`.trim()
}



// format helpers moved to ../../utils/formatJpy

function eventIcon(category) {
  if (category === 'flood' || category === 'climate') return '🌊'
  if (category === 'agriculture') return '🌾'
  if (category === 'ecosystem') return '🌿'
  if (category === 'budget') return '💴'
  if (category === 'resident') return '🏘️'
  if (category === 'policy_effect') return '✓'
  return '!'
}

function categoryLabel(category) {
  if (category === 'flood') return 'Flood'
  if (category === 'climate') return 'Rain'
  if (category === 'agriculture') return 'Food'
  if (category === 'ecosystem') return 'Eco'
  if (category === 'budget') return 'Budget'
  if (category === 'resident') return 'Resident'
  if (category === 'policy_effect') return 'Policy'
  return 'Event'
}