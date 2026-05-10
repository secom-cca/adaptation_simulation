import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { fmtY } from '../../data/indicators.js'
import s from '../../pages/ConsequencePage.module.css'
import own from './CycleReport.module.css'

const REPORT_COLOR = '#5a6a7a'

const METRICS = [
  { key: 'Flood Damage',    icon: '🌊', labelKey: 'report.flood',  good: (v, p) => p != null && v < p },
  { key: 'Crop Yield',      icon: '🌾', labelKey: 'report.crop',   good: (v, p) => p != null && v > p },
  { key: 'Ecosystem Level', icon: '🌿', labelKey: 'report.eco',    good: (v, p) => p != null && v > p },
  { key: 'Resident Burden', icon: '👥', labelKey: 'report.burden', good: (v, p) => p != null && v < p },
]

function avg(rows, key) {
  if (!rows.length) return 0
  return rows.reduce((sum, r) => sum + (r[key] ?? 0), 0) / rows.length
}

export default function CycleReport({ history, year, cycle, onViewDetails }) {
  const { t } = useTranslation()

  const cycleStart = year - 25
  const cycleEnd   = year - 1
  const thisRows   = history.slice(-25)
  const prevRows   = history.length > 25 ? history.slice(-50, -25) : []

  return (
    <div className={s.page} style={{ '--event-color': REPORT_COLOR }}>
      <div className={s.card}>

        <img className={s.eventImage} src="/events/report.png" alt="cycle report" />

        {/* ── Text content ── */}
        <div className={s.content}>
          <div className={s.meta}>
            <span className={s.yearTag}>{cycleStart} – {cycleEnd}</span>
            <span className={s.subtitle}>{t('report.subtitle').replace('{n}', cycle - 1)}</span>
          </div>
          <h1 className={s.title}>{t('report.title')}</h1>

          {/* ── Metric stats row ── */}
          <div className={own.stats}>
            {METRICS.map(m => {
              const val  = avg(thisRows, m.key)
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

          <button className={s.continueBtn} onClick={onViewDetails}>
            {t('report.cta')}
          </button>
        </div>

      </div>
    </div>
  )
}
