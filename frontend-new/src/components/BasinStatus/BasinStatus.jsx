import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { SCORE_BOUNDS } from '../../data/resultScores.js'
import s from './BasinStatus.module.css'

function formatPoints(value) {
  // MayFest 2026: user-facing budget unit is points, rounded to nearest integer for display.
  return `${Math.round(Number(value) || 0)}ポイント`
}

function formatYen(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `${(amount / 100_000_000).toFixed(1)}億円/年`
  if (amount >= 10_000) return `${Math.round(amount / 10_000).toLocaleString()}万円/年`
  return `${Math.round(amount).toLocaleString()}円/年`
}

function rowFloodDamage(row = {}) {
  return Number(row['Flood Damage JPY'] ?? ((row['Flood Damage'] ?? row.flood_damage_cost ?? 0) * 150)) || 0
}

function latestFloodStatusValue(currentValues = {}, history = []) {
  if (history.length >= 25) {
    return history.slice(-25).reduce((sum, row) => sum + rowFloodDamage(row), 0)
  }
  return rowFloodDamage(currentValues)
}

function previousFloodStatusValue(history = []) {
  if (history.length < 50) return null
  return history.slice(-50, -25).reduce((sum, row) => sum + rowFloodDamage(row), 0)
}

function latestTargetYear(history = []) {
  if (history.length >= 75) return 2100
  if (history.length >= 50) return 2075
  return 2050
}

function floodStatusFromScore(value, history = []) {
  const targetYear = latestTargetYear(history)
  const bounds = SCORE_BOUNDS.flood[targetYear] ?? SCORE_BOUNDS.flood[String(targetYear)] ?? SCORE_BOUNDS.flood[2100]
  const good = Number(bounds?.good) || 0
  const bad = Number(bounds?.bad) || 1
  const score = ((bad - value) / Math.max(bad - good, 1e-9)) * 100
  if (score >= 66) return { key: 'status.low', tier: 'good' }
  if (score >= 33) return { key: 'status.medium', tier: 'caution' }
  return { key: 'status.high', tier: 'critical' }
}

export default function BasinStatus({ currentValues, history, budgetRow }) {
  const { t, lang } = useTranslation()
  const prev = history.length > 25 ? history[history.length - 26] : null

  const indicators = [
    {
      icon: '🌊', labelKey: 'basin.flood.label',
      getValue: cv => latestFloodStatusValue(cv, history),
      format: v => floodStatusFromScore(v, history),
    },
    {
      icon: '🌾', labelKey: 'basin.food.label',
      getValue: cv => cv['Crop Yield'] ?? cv.crop_yield ?? 4500,
      format: v => v > 3500 ? { key: 'status.stable', tier: 'good' }
                : v > 2000  ? { key: 'status.declining', tier: 'caution' }
                             : { key: 'status.critical', tier: 'critical' },
    },
    {
      icon: '💴', labelKey: 'basin.burden.label',
      getValue: cv => cv.available_budget_mana ?? cv.availableBudgetPoints ?? 10,
      format: v => v > 5 ? { key: 'status.manageable', tier: 'good' }
                : v > 3 ? { key: 'status.elevated', tier: 'caution' }
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
          const prevVal = ind.labelKey === 'basin.flood.label'
            ? previousFloodStatusValue(history)
            : prev ? ind.getValue(prev) : null
          const trend = prevVal === null ? null : val > prevVal ? 'up' : val < prevVal ? 'down' : 'flat'
          return (
            <div key={ind.labelKey} className={`${s.card} ${s[tier]}`}>
              <span className={s.icon}>{ind.icon}</span>
              <div className={s.info}>
                <div className={s.indLabel}>{ind.labelKey === 'basin.burden.label' ? '政策ポイント' : t(ind.labelKey)}</div>
                <div className={s.status}>
                  <span className={s.statusLabel}>{t(key)}</span>
                  {trend && (
                    <span className={s.trend}>{trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}</span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {budgetRow && (
        <div className={s.budgetNote}>
          <div className={s.budgetHero}>
            <span>{lang === 'ja' ? '使用可能ポイント' : 'Available points'}</span>
            <strong>{`${formatPoints(budgetRow.availableBudgetPoints)} / 10`}</strong>
          </div>
          <div className={s.budgetLine}>
            <span>{lang === 'ja' ? '前25年平均洪水被害' : 'Average flood damage in previous 25 years'}</span>
            <strong>{formatYen(budgetRow.appliedFloodDamage)}</strong>
          </div>
          <div className={s.penaltyGrid}>
            <div><span>{lang === 'ja' ? '人口減少' : 'Population'}</span><strong>{formatPoints(budgetRow.populationPenaltyMana)}</strong></div>
            <div><span>{lang === 'ja' ? '洪水復旧' : 'Flood recovery'}</span><strong>{formatPoints(budgetRow.floodReduction)}</strong></div>
            <div><span>{lang === 'ja' ? '移住後インフラ' : 'Relocation infra'}</span><strong>{formatPoints(budgetRow.migrationReduction)}</strong></div>
          </div>
          <p className={s.budgetHint}>
            {lang === 'ja'
              ? '1ポイントは2,000万円/年を25年間継続する政策費です。洪水復旧ペナルティは、前ターン平均被害額をもとに次ターンの予算制約へ反映します。'
              : '1 point means JPY 20M/year sustained for 25 years. The flood recovery penalty uses average damage in the previous turn.'}
          </p>
        </div>
      )}
    </div>
  )
}

