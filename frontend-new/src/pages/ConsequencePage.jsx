import React from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './ConsequencePage.module.css'

const EVENT_IMAGE_BY_ID = {
  flood_damage: '/events/major_flood_damage.png',
  flood_damage_N: '/events/major_flood_damage.png',
  major_flood_damage: '/events/major_flood_damage.png',
  major_flood_damage_N: '/events/major_flood_damage.png',
  large_flood_damage: '/events/major_flood_damage.png',
  large_flood_damage_N: '/events/major_flood_damage.png',
  severe_flood_damage: '/events/severe_flood_damage.png',
  severe_flood_damage_N: '/events/severe_flood_damage.png',

  crop_production_low: '/events/crop_production_low.png',
  crop_production_critical: '/events/crop_production_critical.png',
  ecosystem_low: '/events/ecosystem_low.png',
  ecosystem_critical: '/events/ecosystem_critical.png',

  forest_area_low: '/events/forest_area_low.png',
  forest_effect_started: '/events/forest_effect_started.png',
  forest_effect_100ha: '/events/forest_effect_100ha.png',
  forest_effect_200ha: '/events/forest_effect_100ha.png',
  forest_effect_300ha: '/events/forest_effect_300ha.png',
  forest_effect_600ha: '/events/forest_effect_300ha.png',
  forest_effect_1000ha: '/events/forest_effect_300ha.png',

  high_risk_low: '/events/high_risk_low.png',
  house_migration_started: '/events/relocation_effect_started.png',
  house_migration_step_N: '/events/relocation_effect_started.png',
  house_migration_near_cap: '/events/relocation_demand.png',
  relocation_effect_started: '/events/relocation_effect_started.png',
  relocation_demand: '/events/relocation_demand.png',

  paddy_dam_started: '/events/paddy_dam_started.png',
  paddy_dam_5mm: '/events/paddy_dam_5mm.png',
  paddy_dam_full: '/events/paddy_dam_full.png',

  levee_started: '/events/levee_started.png',
  levee_completed: '/events/levee_completed.png',
  levee_20mm_step_N: '/events/levee_20mm_step_N.png',

  resident_capacity_low: '/events/resident_capacity_low.png',
  resident_capacity_started: '/events/resident_capacity_started.png',
  resident_capacity_improved: '/events/resident_capacity_improved.png',
  resident_capacity_high: '/events/resident_capacity_high.png',
  resident_capacity_turn_effect: '/events/resident_capacity_improved.png',

  rnd_started: '/events/rnd_started.png',
  rnd_tolerance_improved: '/events/rnd_tolerance_improved.png',
  rnd_tolerance_improved_N: '/events/rnd_tolerance_improved_N.png',

  budget_low: '/events/migration_budget_pressure.png',
  budget_critical: '/events/migration_budget_pressure.png',
  migration_budget_pressure: '/events/migration_budget_pressure.png',
  report: '/events/report.png',
}

const EVENT_VIEW_BY_CATEGORY = {
  flood: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '洪水被害が発生しました',
  },
  climate: {
    color: '#3d6b8f',
    subtitle: 'CLIMATE',
    title: '極端な雨が発生しました',
  },
  crop: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '農作物への影響が出ています',
  },
  ecosystem: {
    color: '#4a7a3a',
    subtitle: 'ECOSYSTEM',
    title: '生態系への影響が出ています',
  },
  policy_effect: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '政策効果が出ています',
  },
  budget: {
    color: '#7a5a8c',
    subtitle: 'BUDGET',
    title: '予算に変化が出ています',
  },
  residents: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '住民への影響が出ています',
  },
  report: {
    color: '#3d6b8f',
    subtitle: 'REPORT',
    title: 'シミュレーションの変化',
  },
}

const CANONICAL_EVENT_ID_BY_PATTERN = [
  { pattern: /^flood_damage_\d+$/, id: 'flood_damage_N' },
  { pattern: /^major_flood_damage_\d+$/, id: 'major_flood_damage_N' },
  { pattern: /^large_flood_damage_\d+$/, id: 'large_flood_damage_N' },
  { pattern: /^severe_flood_damage_\d+$/, id: 'severe_flood_damage_N' },
  { pattern: /^house_migration_step_\d+(point)?$/, id: 'house_migration_step_N' },
  { pattern: /^levee_20mm_step_\d+$/, id: 'levee_20mm_step_N' },
  { pattern: /^rnd_tolerance_improved_\d+$/, id: 'rnd_tolerance_improved_N' },
  { pattern: /^resident_capacity_low_turn\d+_summary$/, id: 'resident_capacity_low' },
  { pattern: /^high_risk_houses_unmanaged_turn\d+_summary$/, id: 'high_risk_low' },
]

export default function ConsequencePage({ sim, onDismiss }) {
  const { t } = useTranslation()
  const currentEvent = sim.gameState.pendingEvents?.[0] ?? {}
  const eventId = resolveEventId(currentEvent)
  const view = viewForEvent(currentEvent)
  const image = EVENT_IMAGE_BY_ID[eventId] ?? EVENT_IMAGE_BY_ID.report
  const body = eventBody(currentEvent)

  return (
    <div className={s.page} style={{ '--event-color': view.color }}>
      <div className={s.card}>
        <img src={image} alt="" className={s.eventImage} />

        <div className={s.content}>
          <div className={s.meta}>
            <span className={s.yearTag}>YEAR {currentEvent.year ?? '-'}</span>
            <span className={s.subtitle}>{view.subtitle}</span>
            {currentEvent.queueTotal > 1 && (
              <span className={s.tag}>
                {currentEvent.queueIndex} / {currentEvent.queueTotal}
              </span>
            )}
          </div>

          <h1 className={s.title}>{currentEvent.title || view.title}</h1>
          <p className={s.body}>{body}</p>

          <button className={s.continueBtn} onClick={onDismiss}>
            {t('consequence.continue')}
          </button>
        </div>
      </div>
    </div>
  )
}

function resolveEventId(event = {}) {
  const rawId = String(event.id ?? event.key ?? 'report')
  if (EVENT_IMAGE_BY_ID[rawId]) return rawId
  return CANONICAL_EVENT_ID_BY_PATTERN.find(({ pattern }) => pattern.test(rawId))?.id ?? 'report'
}

function viewForEvent(event = {}) {
  const category = String(event.category ?? event.group ?? 'report')
  if (category === 'policy_effect') return EVENT_VIEW_BY_CATEGORY.policy_effect
  if (category === 'flood' || category === 'climate') return EVENT_VIEW_BY_CATEGORY[category]
  return EVENT_VIEW_BY_CATEGORY[category] ?? EVENT_VIEW_BY_CATEGORY.report
}

function eventBody(event = {}) {
  if (event.category === 'flood' || event.metric === 'annual_flood_damage_jpy') {
    return event.message || floodBody(event)
  }

  if (event.message) return event.message

  const metricValue = Number.isFinite(Number(event.value)) ? `現在値は${formatNumber(event.value)}です。` : ''
  return metricValue || 'シミュレーション内で重要な変化が発生しました。'
}

function floodBody(event = {}) {
  const currentDamage = toNumber(event.value)
  const baseline = toNumber(event.baselineValue)
  const diff = toNumber(event.diffFromBaseline)
  const reduction = diff > 0 ? diff : Math.max(0, baseline - currentDamage)

  return (
    `この年の洪水被害額は${formatJpy(currentDamage)}でした。` +
    `同じ雨が何も対策しなかった流域に降った場合の被害額${formatJpy(baseline)}と比べると、` +
    `${formatJpy(reduction)}の被害を抑えています。`
  )
}

function formatJpy(value) {
  const amount = toNumber(value)
  if (amount >= 100_000_000) return `約${(amount / 100_000_000).toFixed(1)}億円`
  if (amount >= 10_000) return `約${Math.round(amount / 10_000).toLocaleString()}万円`
  return `約${Math.round(amount).toLocaleString()}円`
}

function formatNumber(value) {
  return Math.round(toNumber(value)).toLocaleString()
}

function toNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}
