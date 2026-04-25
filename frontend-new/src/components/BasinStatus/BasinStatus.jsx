import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './BasinStatus.module.css'

function formatDamage(value, lang) {
  const amount = Number(value) || 0
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M ${lang === 'ja' ? 'USD' : 'USD'}`
  if (amount >= 1_000) return `${Math.round(amount / 1_000)}K ${lang === 'ja' ? 'USD' : 'USD'}`
  return `${Math.round(amount)} USD`
}

function formatPoints(value) {
  return `${Number(value) || 0} pt`
}

export default function BasinStatus({ currentValues, history, budgetRow }) {
  const { t, lang } = useTranslation()
  const prev = history.length > 25 ? history[history.length - 26] : null

  const indicators = [
    {
      icon: '💧', labelKey: 'basin.flood.label',
      getValue: cv => cv['Flood Damage'] ?? cv.flood_damage_cost ?? 0,
      format: v => v < 1e7 ? { key: 'status.low', tier: 'good' }
                : v < 2e8 ? { key: 'status.medium', tier: 'caution' }
                           : { key: 'status.high', tier: 'critical' },
    },
    {
      icon: '🌾', labelKey: 'basin.food.label',
      getValue: cv => cv['Crop Yield'] ?? cv.crop_yield ?? 4500,
      format: v => v > 3500 ? { key: 'status.stable', tier: 'good' }
                : v > 2000  ? { key: 'status.declining', tier: 'caution' }
                             : { key: 'status.critical', tier: 'critical' },
    },
    {
      icon: '👥', labelKey: 'basin.burden.label',
      getValue: cv => cv['Resident Burden'] ?? cv.resident_burden ?? 0,
      format: v => v < 500  ? { key: 'status.manageable', tier: 'good' }
                : v < 2000  ? { key: 'status.elevated', tier: 'caution' }
                             : { key: 'status.severe', tier: 'critical' },
    },
    {
      icon: '🌿', labelKey: 'basin.eco.label',
      getValue: cv => cv['Ecosystem Level'] ?? cv.ecosystem_level ?? 1000,
      format: v => v > 70 ? { key: 'status.healthy', tier: 'good' }
                : v > 40  ? { key: 'status.stressed', tier: 'caution' }
                           : { key: 'status.degraded', tier: 'critical' },
    },
  ]

  return (
    <div className={s.panel}>
      <div className={s.header}>{t('basin.header')}</div>
      <div className={s.cards}>
        {indicators.map(ind => {
          const val = ind.getValue(currentValues)
          const { key, tier } = ind.format(val)
          const prevVal = prev ? ind.getValue(prev) : null
          const trend = prevVal === null ? null : val > prevVal ? 'up' : val < prevVal ? 'down' : 'flat'
          return (
            <div key={ind.labelKey} className={`${s.card} ${s[tier]}`}>
              <span className={s.icon}>{ind.icon}</span>
              <div className={s.info}>
                <div className={s.indLabel}>{t(ind.labelKey)}</div>
                <div className={s.status}>
                  <span className={s.statusLabel}>{t(key)}</span>
                  {trend && (
                    <span className={s.trend}>
                      {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      {budgetRow && (
        <div className={s.budgetNote}>
          <div className={s.budgetLine}>
            <span>{t('budget.appliedFloodDamage')}</span>
            <strong>{formatDamage(budgetRow.appliedFloodDamage, lang)}</strong>
          </div>
          <div className={s.budgetLine}>
            <span>{t('budget.pointReduction')}</span>
            <strong>
              {formatPoints(budgetRow.totalBudgetReduction)}
              <span className={s.budgetBreakdown}>
                {` (${t('budget.floodShort')} ${formatPoints(budgetRow.floodReduction)}, ${t('budget.relocationShort')} ${formatPoints(budgetRow.migrationReduction)})`}
              </span>
            </strong>
          </div>
          <div className={s.budgetLine}>
            <span>{t('budget.availablePoints')}</span>
            <strong>{`${formatPoints(budgetRow.availableBudgetPoints)} / 10 pt`}</strong>
          </div>
          <p className={s.budgetHint}>{t('budget.ruleNote')}</p>
        </div>
      )}
    </div>
  )
}
