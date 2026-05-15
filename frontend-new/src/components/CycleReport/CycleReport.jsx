import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { fmtY } from '../../data/indicators.js'
import s from '../../pages/ConsequencePage.module.css'
import own from './CycleReport.module.css'

const REPORT_COLOR = '#5a6a7a'

const METRICS = [
  { key: 'Flood Damage JPY', icon: '🌊', labelKey: 'report.flood', good: (v, p) => p != null && v < p },
  { key: 'Crop Yield', icon: '🌾', labelKey: 'report.crop', good: (v, p) => p != null && v > p },
  { key: 'Ecosystem Level', icon: '🌿', labelKey: 'report.eco', good: (v, p) => p != null && v > p },
  { key: 'Resident Burden', icon: '💴', labelKey: 'report.burden', good: (v, p) => p != null && v < p },
]

function avg(rows, key) {
  if (!rows.length) return 0
  return rows.reduce((sum, r) => sum + (r[key] ?? 0), 0) / rows.length
}

export default function CycleReport({ history, year, cycle, onViewDetails }) {
  const { t } = useTranslation()
  const cycleStart = year - 25
  const cycleEnd = year - 1
  const thisRows = history.slice(-25)
  const prevRows = history.length > 25 ? history.slice(-50, -25) : []
  const cycleEvents = collectCycleEvents(thisRows)

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
              const val = avg(thisRows, m.key)
              const prev = prevRows.length ? avg(prevRows, m.key) : null
              const delta = prev != null ? val - prev : null
              const isGood = m.good(val, prev)
              return (
                <div key={m.key} className={own.stat}>
                  <span className={own.statIcon}>{m.icon}</span>
                  <span className={own.statLabel}>{t(m.labelKey)}</span>
                  <span className={own.statVal}>{fmtY(val)}</span>
                  {delta != null && (
                    <span className={`${own.statDelta} ${isGood ? own.good : own.bad}`}>
                      {delta > 0 ? '+' : ''}{fmtY(delta)}
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          <div className={own.eventSection}>
            <div className={own.eventHeader}>
              <span>{cycleEvents.length > 0 ? 'この25年で起きたイベント' : 'この25年のイベント'}</span>
              <strong>{cycleEvents.length}</strong>
            </div>
            <div className={own.eventCards}>
              {cycleEvents.length > 0 ? cycleEvents.slice(0, 6).map((ev, i) => (
                <div key={`${ev.year}-${ev.title}-${i}`} className={`${own.eventCard} ${own[ev.severity]}`}>
                  <div className={own.eventTop}>
                    <span className={own.eventIcon}>{ev.icon}</span>
                    <span className={own.eventYear}>{ev.year}</span>
                    <span className={own.eventCategory}>{ev.category}</span>
                  </div>
                  <div className={own.eventTitle}>{ev.title}</div>
                  <p className={own.eventBody}>{ev.body}</p>
                </div>
              )) : (
                <div className={`${own.eventCard} ${own.ok}`}>
                  <div className={own.eventTop}>
                    <span className={own.eventIcon}>✓</span>
                    <span className={own.eventYear}>{cycleStart}-{cycleEnd}</span>
                    <span className={own.eventCategory}>Status</span>
                  </div>
                  <div className={own.eventTitle}>大きな閾値イベントはありません</div>
                  <p className={own.eventBody}>この期間は、参加者に強調して知らせる水準の洪水・生態系・食糧生産・予算イベントは発生しませんでした。</p>
                </div>
              )}
            </div>
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
      const rainText = maxRain >= 160 ? `この年は最大${maxRain.toFixed(0)}mmの極端降雨が発生し、` : ''
      const damageText = floodDamage > 0 ? `洪水被害は${formatJpyInline(floodDamage)}でした。` : ''
      return `${rainText}${damageText} その影響で農作物生産が初期水準を下回っています。`
    }
  }
  const value = ev.metric?.includes('Damage') ? `${formatJpy(ev.value)} ` : ''
  return `${value}${ev.message ?? ''}`.trim()
}

function formatJpyInline(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `約${(amount / 100_000_000).toFixed(1)}億円`
  if (amount >= 10_000) return `約${Math.round(amount / 10_000).toLocaleString()}万円`
  return `約${Math.round(amount).toLocaleString()}円`
}

function formatJpy(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `被害額 約${(amount / 100_000_000).toFixed(1)}億円。`
  if (amount >= 10_000) return `被害額 約${Math.round(amount / 10_000).toLocaleString()}万円。`
  return `被害額 約${Math.round(amount).toLocaleString()}円。`
}

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
