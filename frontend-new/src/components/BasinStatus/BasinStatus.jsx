import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './BasinStatus.module.css'

function formatPoints(value) {
  return `${(Number(value) || 0).toFixed(1)} mana`
}

function formatYen(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `${(amount / 100_000_000).toFixed(1)}億円/年`
  if (amount >= 10_000) return `${Math.round(amount / 10_000).toLocaleString()}万円/年`
  return `${Math.round(amount).toLocaleString()}円/年`
}

export default function BasinStatus({ currentValues, history, budgetRow }) {
  const { t, lang } = useTranslation()
  const prev = history.length > 25 ? history[history.length - 26] : null

  const indicators = [
    {
      icon: '🌊', labelKey: 'basin.flood.label',
      getValue: cv => cv['Flood Damage JPY'] ?? ((cv['Flood Damage'] ?? cv.flood_damage_cost ?? 0) * 150),
      format: v => v < 100_000_000 ? { key: 'status.low', tier: 'good' }
                : v < 200_000_000 ? { key: 'status.medium', tier: 'caution' }
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
            <span>{lang === 'ja' ? '使用可能マナ' : 'Available mana'}</span>
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
              ? '1マナは2,000万円/年を25年間継続する政策費です。洪水復旧ペナルティは、前ターン平均被害額をもとに次ターンの予算制約へ反映します。'
              : '1 mana means JPY 20M/year sustained for 25 years. The flood recovery penalty uses average damage in the previous turn.'}
          </p>
        </div>
      )}
    </div>
  )
}
