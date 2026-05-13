import React from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './ConsequencePage.module.css'

const EVENT_META = {
  flood: { color: '#3d6b8f', image: '/events/major_flood_damage.png.png', subtitle: 'RIVER FLOODING', title: { ja: '河川氾濫', en: 'River flooding' } },
  climate: { color: '#3d6b8f', image: '/events/extreme_rain.png.png', subtitle: 'EXTREME RAIN', title: { ja: '極端降雨', en: 'Extreme rainfall' } },
  agriculture: { color: '#8c6b1a', image: '/events/crop_production_low.png.png', subtitle: 'AGRICULTURE', title: { ja: '農作物生産', en: 'Agriculture' } },
  ecosystem: { color: '#4a7a3a', image: '/events/ecosystem_low.png.png', subtitle: 'ECOSYSTEM', title: { ja: '生態系', en: 'Ecosystem change' } },
  budget: { color: '#7a5a8c', image: '/events/budget_low.png.png', subtitle: 'BUDGET', title: { ja: '予算制約', en: 'Budget constraint' } },
  resident: { color: '#8c6b3d', image: '/events/relocation_effect_started.png.png', subtitle: 'RESIDENTS', title: { ja: '住民・住宅', en: 'Residents' } },
  policy_effect: { color: '#4a8c5c', image: '/events/levee_completed.png.png', subtitle: 'POLICY EFFECT', title: { ja: '政策効果', en: 'Policy effect' } },
  drought: { color: '#8c6b1a', image: '/events/crop_production_low.png.png', subtitle: 'FOOD PRODUCTION', title: { ja: '食料生産の低下', en: 'Food production decline' } },
  water_quality: { color: '#4a7a3a', image: '/events/ecosystem_low.png.png', subtitle: 'ECOSYSTEM', title: { ja: '生態系の悪化', en: 'Ecosystem decline' } },
}

const EVENT_IMAGE_BY_ID = {
  levee_started: '/events/levee_completed.png.png',
  levee_completed: '/events/levee_completed.png.png',
  forest_investment_started: '/events/forest_started.svg',
  forest_effect_started: '/events/forest_effect_started.png.png',
  forest_area_low: '/events/ecosystem_low.png.png',
  forest_policy_needed: '/events/ecosystem_low.png.png',
  relocation_effect_started: '/events/relocation_effect_started.png.png',
  high_risk_houses_unmanaged: '/events/relocation_effect_started.png.png',
  high_risk_houses_unmanaged_turn2_summary: '/events/relocation_effect_started.png.png',
  resident_capacity_started: '/events/resident_capacity_high.png.png',
  resident_capacity_improved: '/events/resident_capacity_high.png.png',
  resident_capacity_high: '/events/resident_capacity_high.png.png',
  resident_capacity_low: '/events/evacuation_low.svg',
  resident_capacity_low_turn2_summary: '/events/evacuation_low.svg',
  paddy_dam_started: '/events/paddy_dam_started.png.png',
  paddy_dam_5mm: '/events/paddy_dam_started.png.png',
  rnd_started: '/events/rnd_tolerance_improved.png.png',
  rnd_tolerance_improved: '/events/rnd_tolerance_improved.png.png',
  budget_low: '/events/budget_low.png.png',
  budget_critical: '/events/budget_critical.png.png',
  migration_budget_pressure: '/events/budget_low.png.png',
  ecosystem_low: '/events/ecosystem_low.png.png',
  ecosystem_critical: '/events/ecosystem_critical.png.png',
  crop_production_low: '/events/crop_production_low.png.png',
  crop_production_critical: '/events/crop_production_critical.png.png',
  major_flood_damage: '/events/major_flood_damage.png.png',
  severe_flood_damage: '/events/severe_flood_damage.png.png',
  relocation_demand: '/events/relocation_effect_started.png.png',
  urban_convenience_low: '/events/urban_convenience_low.png.png',
}

export default function ConsequencePage({ sim, onDismiss }) {
  const { t, lang } = useTranslation()
  const currentEvent = sim.gameState.pendingEvents?.[0]
  const ev = normalizeEvent(currentEvent, lang)
  const meta = EVENT_META[ev.key] ?? EVENT_META.flood
  const imageSrc = eventImage(ev, meta)

  return (
    <div className={s.page} style={{ '--event-color': meta.color }}>
      <div className={s.card}>
        <img
          src={imageSrc}
          alt=""
          className={s.eventImage}
          onError={event => {
            event.currentTarget.onerror = null
            event.currentTarget.src = fallbackImage(ev, meta)
          }}
        />

        <div className={s.content}>
          <div className={s.meta}>
            <span className={s.yearTag}>YEAR {ev.year}</span>
            <span className={s.subtitle}>{ev.subtitle ?? meta.subtitle}</span>
            {currentEvent?.queueTotal > 1 && <span className={s.tag}>{currentEvent.queueIndex} / {currentEvent.queueTotal}</span>}
          </div>
          <h1 className={s.title}>{ev.title ?? meta.title[lang] ?? meta.title.en}</h1>
          <p className={s.body}>{ev.body}</p>
          <button className={s.continueBtn} onClick={onDismiss}>
            {t('consequence.continue')}
          </button>
        </div>
      </div>
    </div>
  )
}



function normalizeEvent(event, lang) {
  if (event?.type === 'model_event') {
    const key = event.category ?? event.key ?? 'flood'
    const copy = modelEventCopy(event, lang)
    return {
      key,
      id: event.id,
      year: event.year ?? '-',
      subtitle: categorySubtitle(key),
      title: copy.title ?? event.title,
      body: copy.body ?? formatModelMessage(event),
    }
  }

  if (event?.key === 'drought') {
    return {
      key: 'drought',
      year: event.year ?? '-',
      title: lang === 'ja' ? '食料生産の低下' : 'Food production decline',
      body: lang === 'ja'
        ? '高温や水不足の影響で食料生産が低下しています。農業R&Dは高温耐性を高め、この低下を抑えます。'
        : 'Food production has fallen because of heat and water stress. Agricultural R&D improves heat tolerance over time.',
    }
  }

  if (event?.key === 'water_quality') {
    return {
      key: 'water_quality',
      year: event.year ?? '-',
      title: lang === 'ja' ? '生態系の悪化' : 'Ecosystem decline',
      body: lang === 'ja'
        ? '生態系指標が閾値を下回りました。森林保全は時間遅れで保水力と生態系を改善します。'
        : 'The ecosystem indicator has declined. Forest restoration improves ecosystems and retention with a delay.',
    }
  }

  const amount = formatJpy(event?.value)
  return {
    key: 'flood',
    year: event?.year ?? '-',
    title: lang === 'ja' ? '河川氾濫' : 'River flooding',
    body: lang === 'ja'
      ? `この25年で洪水被害額が${amount}に達しました。復旧費・避難支援・再建対応により、次ターンの政策予算も圧迫されます。`
      : `Flood damage reached ${amount} in this 25-year period. Recovery, evacuation support, and rebuilding will reduce next-turn policy capacity.`,
  }
}

function modelEventCopy(event, lang) {
  if (lang !== 'ja') return { title: event.title, body: formatModelMessage(event) }

  const id = event.id ?? ''
  const value = Number(event.value) || 0
  const threshold = Number(event.threshold) || 0

  if (id.startsWith('extreme_rain_frequency_')) {
    return {
      title: '極端降雨の発生回数が増えています',
      body: `この年は極端降雨が${value.toFixed(0)}回発生しました。極端降雨が1回以上発生した年として記録し、防災訓練・堤防・田んぼダムなどの対策検討につなげます。`,
    }
  }
  if (id.startsWith('heavy_rain_')) {
    return {
      title: '極端降雨が発生しました',
      body: `最大${value.toFixed(0)}mmの極端降雨が発生しました。堤防・田んぼダム・森林保全で越流水を抑えられている場合、その分だけ洪水被害や農地・生態系への影響は小さくなります。`,
    }
  }
  if (id === 'forest_policy_needed') return { title: '森林保全の遅れが目立っています', body: `森林面積が約${value.toFixed(0)}haとなり、目安の${threshold.toFixed(0)}haを下回っています。森林保全は保水力・流出抑制・生態系を支えるため、早めの継続投資が重要です。` }
  if (id === 'resident_capacity_low_turn2_summary') return { title: '住民の防災対応力が低い状態です', body: `住民の防災対応力が${value.toFixed(2)}にとどまっています。防災訓練は小〜中規模の洪水被害を軽減しやすくします。` }
  if (id === 'high_risk_houses_unmanaged_turn2_summary') return { title: '高リスク住宅が多く残っています', body: `高リスク住宅が約${value.toFixed(0)}戸残り、目安の${threshold.toFixed(0)}戸を超えています。住宅移転は洪水被害を直接下げますが、将来のインフラ維持費とのトレードオフがあります。` }

  if (id.startsWith('extreme_rain_')) {
    return {
      title: '極端降雨が発生しました',
      body: `${value.toFixed(0)}mmの極端降雨が発生しました。堤防・田んぼダム・森林で越流水を減らせている場合、その分だけ洪水被害や農地・生態系への衝撃は小さくなります。`,
    }
  }
  if (id.startsWith('major_flood_damage_') || id === 'major_flood_damage') {
    return { title: '大規模な洪水被害が発生しました', body: `洪水被害額が${formatJpy(value)}となり、閾値${formatJpy(threshold)}を超えました。表示額は現在の対策で軽減した後の被害です。` }
  }
  if (id.startsWith('severe_flood_damage_') || id === 'severe_flood_damage') {
    return { title: '甚大な洪水被害が発生しました', body: `洪水被害額が${formatJpy(value)}となり、甚大被害の閾値${formatJpy(threshold)}を超えました。復旧費が次ターン以降の予算を強く圧迫します。` }
  }
  if (id === 'crop_production_low') return { title: '高温により農作物生産が低下しています', body: `極端降雨年の一時的な被害を除いた高温由来の作物生産が、基準生産力の約${(value * 100).toFixed(0)}%まで下がりました。農業R&Dはこの閾値を避けるための対策です。` }
  if (id === 'crop_production_critical') return { title: '農業生産が深刻に低下しています', body: `高温由来の作物生産が基準生産力の約${(value * 100).toFixed(0)}%まで下がりました。適応品種や栽培技術の不足が食料生産を押し下げています。` }
  if (id === 'ecosystem_low') return { title: '生態系への負荷が高まっています', body: `生態系指標が${value.toFixed(1)}となり、閾値${threshold.toFixed(1)}を下回りました。森林保全は保水力と生態系を同時に支えます。` }
  if (id === 'ecosystem_critical') return { title: '生態系指標が深刻に低下しています', body: `生態系指標が${value.toFixed(1)}となり、危機的な閾値${threshold.toFixed(1)}を下回りました。` }
  if (id === 'forest_area_low') return { title: '森林面積が低下しています', body: `森林面積が約${value.toFixed(0)}haとなり、閾値${threshold.toFixed(0)}haを下回りました。保水力・洪水緩和・生態系の長期的な支えが弱まっています。` }
  if (id === 'resident_capacity_low') return { title: '住民防災能力が低い状態です', body: `住民防災能力が${value.toFixed(2)}にとどまっています。防災訓練は小中規模の洪水被害を軽減しやすくします。` }
  if (id === 'high_risk_houses_unmanaged') return { title: '高リスク住宅が多く残っています', body: `高リスク住宅が約${value.toFixed(0)}戸残り、閾値${threshold.toFixed(0)}戸を超えています。住宅移転は洪水被害を直接下げますが、将来のインフラ維持費とのトレードオフがあります。` }
  if (id === 'budget_low' || id === 'migration_budget_pressure') return { title: '政策予算が縮小しています', body: `利用可能な政策予算や移転後インフラ費用に注意が必要です。現在の関連指標は${value.toFixed(2)}マナです。` }
  if (id === 'budget_critical') return { title: '政策予算が大きく縮小しています', body: `利用可能な政策予算が${value.toFixed(2)}マナまで低下しました。人口減少、復旧費、移転後インフラ費用の影響を受けています。` }
  if (id.startsWith('rnd_tolerance_improved_')) return { title: '高温適応技術が普及しました', body: `農業R&Dの蓄積により、高温耐性が${value.toFixed(1)}度まで向上しました。` }
  if (id.startsWith('levee_20mm_step_') || id === 'levee_completed') return { title: '堤防・河川改修が進みました', body: `堤防・河川改修により防御水準が${value.toFixed(0)}mmになりました。大雨時の越流水を減らします。` }
  if (id === 'paddy_dam_5mm') return { title: '田んぼダムの効果が見え始めました', body: `田んぼダムの貯留効果が約${value.toFixed(1)}mmに達しました。分散型の流域治水として洪水ピークを抑えます。` }
  if (id === 'relocation_demand') return { title: '住宅移転ニーズが高まっています', body: '大規模洪水により、高リスク地域に残る住宅の移転ニーズが高まっています。' }

  return { title: event.title, body: formatModelMessage(event) }
}

function eventImage(event, meta) {
  const id = event?.id ?? ''
  const imageId = imageIdFromEventId(id)
  if (imageId) return `/events/${imageId}.png`
  return normalizeImagePath(EVENT_IMAGE_BY_ID[id] ?? meta.image)
}

function fallbackImage(event, meta) {
  const id = event?.id ?? ''
  const imageId = imageIdFromEventId(id)
  if (imageId) return `/events/${imageId}.png`
  return normalizeImagePath(meta.image)
}

function imageIdFromEventId(id = '') {
  if (!id) return null

  if (id.startsWith('heavy_rain_')) return 'heavy_rain'
  if (id.startsWith('extreme_rain_frequency_')) return 'extreme_rain_frequency'
  if (id.startsWith('extreme_rain_') || id.startsWith('extreme_rain_record_')) return 'extream_rain'
  if (id.startsWith('flood_damage_')) return 'major_flood_damage'
  if (id.startsWith('major_flood_damage_')) return 'major_flood_damage'
  if (id.startsWith('severe_flood_damage_')) return 'severe_flood_damage'
  if (id.startsWith('forest_effect_100ha')) return 'forest_effect_100ha'
  if (id.startsWith('forest_effect_300ha')) return 'forest_effect_300ha'
  if (id.startsWith('levee_20mm_step_')) return 'levee_20mm_step_N'
  if (id.startsWith('rnd_tolerance_improved_')) return 'rnd_tolerance_improved_N'

  const aliases = {
    forest_investment_started: 'forest_effect_started',
    extreme_rain: 'extream_rain',
    high_risk_houses_unmanaged: 'high_risk_low',
    high_risk_houses_unmanaged_turn2_summary: 'high_risk_low',
    resident_capacity_low_turn2_summary: 'resident_capacity_low',
    rnd_tolerance_improved: 'rnd_tolerance_improved',
  }
  return aliases[id] ?? id
}

function normalizeImagePath(path = '') {
  return path
    .replace('.png.png', '.png')
    .replace('/events/extreme_rain.png', '/events/extream_rain.png')
    .replace('/events/crop_production_low.png', '/events/crop_production_critical.png')
    .replace('/events/budget_low.png', '/events/migration_budget_pressure.png')
    .replace('/events/budget_critical.png', '/events/migration_budget_pressure.png')
    .replace('/events/policy_effect.svg', '/events/levee_completed.png')
    .replace(/\.svg$/, '.png')
}

function formatModelMessage(event) {
  const valueText = event.metric?.includes('Damage') ? `${formatJpy(event.value)} ` : ''
  return `${valueText}${event.message ?? ''}`.trim()
}

function categorySubtitle(category) {
  if (category === 'climate') return 'EXTREME RAIN'
  if (category === 'flood') return 'RIVER FLOODING'
  if (category === 'policy_effect') return 'POLICY EFFECT'
  if (category === 'agriculture') return 'AGRICULTURE'
  if (category === 'ecosystem') return 'ECOSYSTEM'
  if (category === 'budget') return 'BUDGET'
  if (category === 'resident') return 'RESIDENTS'
  return 'MODEL EVENT'
}

function formatJpy(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `約${(amount / 100_000_000).toFixed(1)}億円`
  if (amount >= 10_000) return `約${Math.round(amount / 10_000).toLocaleString()}万円`
  return `約${Math.round(amount).toLocaleString()}円`
}
