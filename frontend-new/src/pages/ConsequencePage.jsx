import React from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './ConsequencePage.module.css'

/**
 * 画像対応表
 *
 * 原則：
 * - イベントIDごとに、ここで必ず対応するPNGを指定する。
 * - 画像対応を自動推測しない。
 * - 新しいイベントを追加したら、この表に1行追加する。
 * - 表示画像はこの表だけを正とする。
 */
const EVENT_IMAGE_BY_ID = {
  // 洪水・降雨
  flood_damage: '/events/major_flood_damage.png',
  major_flood_damage: '/events/major_flood_damage.png',
  severe_flood_damage: '/events/severe_flood_damage.png',
  large_flood_damage: '/events/major_flood_damage.png',
  large_flood_damage_N: '/events/major_flood_damage.png',

  // 年付き洪水イベント用の代表画像
  flood_damage_N: '/events/major_flood_damage.png',
  major_flood_damage_N: '/events/major_flood_damage.png',
  severe_flood_damage_N: '/events/severe_flood_damage.png',

  // 農作物生産
  crop_production_low: '/events/crop_production_low.png',
  crop_production_critical: '/events/crop_production_critical.png',

  // 生態系
  ecosystem_low: '/events/ecosystem_low.png',
  ecosystem_critical: '/events/ecosystem_critical.png',

  // 森林
  forest_area_low: '/events/forest_area_low.png',
  forest_effect_started: '/events/forest_effect_started.png',

  // 森林効果イベント：200 / 600 / 1000ha
  forest_effect_200ha: '/events/forest_effect_100ha.png',
  forest_effect_600ha: '/events/forest_effect_300ha.png',
  forest_effect_1000ha: '/events/forest_effect_300ha.png',

  // 旧基準の画像を残している場合の互換用
  forest_effect_100ha: '/events/forest_effect_100ha.png',
  forest_effect_300ha: '/events/forest_effect_300ha.png',

  // 住宅移転・高リスク住宅
  high_risk_low: '/events/high_risk_low.png',
  house_migration_started: '/events/relocation_effect_started.png',
  house_migration_step_N: '/events/house_migration_step_N.png',
  house_migration_near_cap: '/events/relocation_demand.png',
  relocation_effect_started: '/events/relocation_effect_started.png',
  relocation_demand: '/events/relocation_demand.png',

  // 田んぼダム
  paddy_dam_started: '/events/paddy_dam_started.png',
  paddy_dam_5mm: '/events/paddy_dam_5mm.png',
  paddy_dam_full: '/events/paddy_dam_full.png',

  // 堤防・河川改修
  levee_started: '/events/levee_started.png',
  levee_completed: '/events/levee_completed.png',
  levee_20mm_step_N: '/events/levee_20mm_step_N.png',

  // 防災対応力・防災訓練
  resident_capacity_low: '/events/resident_capacity_low.png',
  resident_capacity_started: '/events/resident_capacity_started.png',
  resident_capacity_improved: '/events/resident_capacity_improved.png',
  resident_capacity_high: '/events/resident_capacity_high.png',
  resident_capacity_turn_effect: '/events/resident_capacity_improved.png',

  // 農業R&D
  rnd_started: '/events/rnd_started.png',
  rnd_tolerance_improved: '/events/rnd_tolerance_improved.png',
  rnd_tolerance_improved_N: '/events/rnd_tolerance_improved_N.png',

  // 予算
  budget_low: '/events/migration_budget_pressure.png',
  budget_critical: '/events/migration_budget_pressure.png',
  migration_budget_pressure: '/events/migration_budget_pressure.png',

  // レポート・その他
  report: '/events/report.png',
}

/**
 * イベント表示定義
 *
 * ここでは画像を直接持たせない。
 * 画像は必ず EVENT_IMAGE_BY_ID[eventId] から取得する。
 */
const EVENT_VIEW_BY_ID = {
  // 洪水・降雨
  flood_damage: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },
  major_flood_damage: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '大きな洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の大きな被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },
  large_flood_damage: {
  color: '#3d6b8f',
  subtitle: 'RIVER FLOODING',
  title: 'かなり大きな洪水被害が発生しました',
  body: event =>
    `洪水により、住宅被害などを中心に${formatJpy(event.value)}のかなり大きな被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
},

large_flood_damage_N: {
  color: '#3d6b8f',
  subtitle: 'RIVER FLOODING',
  title: 'かなり大きな洪水被害が発生しました',
  body: event =>
    `洪水により、住宅被害などを中心に${formatJpy(event.value)}のかなり大きな被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
},
  severe_flood_damage: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '甚大な洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の甚大な被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },
  flood_damage_N: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },
  major_flood_damage_N: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '大きな洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の大きな被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },
  severe_flood_damage_N: {
    color: '#3d6b8f',
    subtitle: 'RIVER FLOODING',
    title: '甚大な洪水被害が発生しました',
    body: event =>
      `洪水により、住宅被害などを中心に${formatJpy(event.value)}の甚大な被害が生じました。${floodDiffText(event)}治水対策や被害を軽減するための対策を取る必要があります。`,
  },

  // 農作物生産
  crop_production_low: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '農作物生産が低下しています',
    body: event =>
      `高温や水害の影響により、農作物生産性が${formatNumber(event.value)}kg/haまで下がっています。${gainText(event, 'kg/ha')}農業R&Dや治水対策など、被害を軽減するための対策を取る必要があります。`,
  },
  crop_production_critical: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '農作物生産が深刻に低下しています',
    body: event =>
      `高温や水害の影響により、農作物生産性が${formatNumber(event.value)}kg/haまで下がっています。${gainText(event, 'kg/ha')}農業R&Dや治水対策など、被害を軽減するための対策を取る必要があります。`,
  },

  // 生態系
  ecosystem_low: {
    color: '#4a7a3a',
    subtitle: 'ECOSYSTEM',
    title: '生態系への負荷が高まっています',
    body: event =>
      `生態系指標が${formatOneDecimal(event.value)}まで低下しています。${gainText(event, 'ポイント')}森林保全や治水対策とのバランスを見ながら、被害を軽減するための対策を取る必要があります。`,
  },
  ecosystem_critical: {
    color: '#4a7a3a',
    subtitle: 'ECOSYSTEM',
    title: '生態系が深刻に悪化しています',
    body: event =>
      `生態系指標が${formatOneDecimal(event.value)}まで低下しています。${gainText(event, 'ポイント')}森林保全や治水対策とのバランスを見ながら、被害を軽減するための対策を取る必要があります。`,
  },

  // 森林
  forest_area_low: {
    color: '#4a7a3a',
    subtitle: 'ECOSYSTEM',
    title: '森林面積が低下しています',
    body: event =>
      `森林面積が約${formatNumber(event.value)}haまで低下しています。森林の減少は、雨水を一時的にためる力の低下と、生きもののすみかの減少という2つの面で地域に影響します。`,
  },
  forest_effect_started: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が見え始めました',
    body:
      '過去に植えた木が成長し始め、森林面積が回復してきました。森林は、雨水を一時的にためる力と、生きもののすみかを支える力の両面で地域に関わります。',
  },
  forest_effect_100ha: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が広がっています',
    body: event =>
      `成長した森林面積が約${formatNumber(event.value)}haに達しました。森林保全の効果が、流域全体の水循環と生きもののすみかを支える形で広がっています。`,
  },
  forest_effect_200ha: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が広がっています',
    body: event =>
      `成長した森林面積が約${formatNumber(event.value)}haに達しました。森林保全の効果が、流域全体の水循環と生きもののすみかを支える形で広がっています。`,
  },
  forest_effect_300ha: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が広がっています',
    body: event =>
      `成長した森林面積が約${formatNumber(event.value)}haに達しました。森林保全の効果が、流域全体の水循環と生きもののすみかを支える形で広がっています。`,
  },
  forest_effect_600ha: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が大きく広がっています',
    body: event =>
      `成長した森林面積が約${formatNumber(event.value)}haに達しました。森林保全の効果が、流域全体の水循環と生きもののすみかを支える形で広がっています。`,
  },
  forest_effect_1000ha: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '森林保全の効果が流域全体に広がっています',
    body: event =>
      `成長した森林面積が約${formatNumber(event.value)}haに達しました。森林保全の効果が、流域全体の水循環と生きもののすみかを支える形で広がっています。`,
  },

  // 住宅移転・高リスク住宅
  high_risk_low: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '高リスク地域に住宅が残っています',
    body:
      '洪水リスクの高い地域に住宅が残っているため、大雨時に住宅被害が発生しやすい状態です。住宅移転や土地利用の見直しにより、被害を受けやすい住宅を減らすことができます。',
  },
  house_migration_started: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '高リスク地域からの移転が進み始めています',
    body: event => migrationBody(event, false),
  },
  relocation_effect_started: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '高リスク地域からの移転が進み始めています',
    body: event => migrationBody(event, false),
  },
  house_migration_step_N: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '高リスク地域からの移転が進んでいます',
    body: event => migrationBody(event, false),
  },
  house_migration_near_cap: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '高リスク地域からの移転が大きく進みました',
    body: event => migrationBody(event, true),
  },
  relocation_demand: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '高リスク地域からの移転が大きく進みました',
    body: event => migrationBody(event, true),
  },

  // 田んぼダム
  paddy_dam_started: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '田んぼダムの導入を始めました',
    body:
      '水田に雨水を一時的にためる取り組みが始まりました。導入面積が広がるほど、洪水時の流出を抑える効果が大きくなります。',
  },
  paddy_dam_5mm: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '田んぼダムの効果が出てきました',
    body: event =>
      `田んぼダムの導入面積が広がり、洪水時の流出を約${formatOneDecimal(event.value)}mm分抑えられる水準に達しました。`,
  },
  paddy_dam_full: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '田んぼダムが最大効果に近づきました',
    body: event =>
      `田んぼダムの導入面積が広がり、洪水時の流出を約${formatOneDecimal(event.value)}mm分抑えられる水準に達しました。`,
  },

  // 堤防・河川改修
  levee_started: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '堤防・河川改修を始めました',
    body:
      '堤防・河川改修への投資が始まりました。効果が出るまでには時間がかかりますが、完成すると大雨時の越流水を減らします。',
  },
  levee_completed: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '堤防・河川改修が一段階進みました',
    body: event =>
      `累積投資により、堤防・河川改修の防御水準が約${formatNumber(event.value)}mmになりました。大雨時の越流水を減らします。`,
  },
  levee_20mm_step_N: {
    color: '#4a8c5c',
    subtitle: 'POLICY EFFECT',
    title: '堤防・河川改修が一段階進みました',
    body: event =>
      `累積投資により、堤防・河川改修の防御水準が約${formatNumber(event.value)}mmになりました。大雨時の越流水を減らします。`,
  },

  // 防災対応力・防災訓練
  resident_capacity_low: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '防災対応を理解している人が少ない状態です',
    body:
      '避難訓練や防災訓練が十分に行われておらず、洪水時にどう行動すればよいかを理解している住民が少ない状態です。防災訓練を行うことで、洪水時の被害を軽減しやすくなります。',
  },
  resident_capacity_started: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '防災訓練を始めました',
    body:
      '避難訓練や防災訓練により、洪水時にどう行動すればよいかを理解している住民が増えています。洪水による被害を軽減しやすい状態になってきました。',
  },
  resident_capacity_improved: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '防災訓練の効果が出ています',
    body:
      '避難訓練や防災訓練により、洪水時にどう行動すればよいかを理解している住民が増えています。洪水による被害を軽減しやすい状態になってきました。',
  },
  resident_capacity_high: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '防災対応力が高まっています',
    body:
      '避難訓練や防災訓練により、洪水時にどう行動すればよいかを理解している住民が多くなっています。洪水による人的・住宅被害を軽減しやすい状態です。',
  },
  resident_capacity_turn_effect: {
    color: '#8c6b3d',
    subtitle: 'RESIDENTS',
    title: '防災訓練の効果が出ています',
    body:
      '避難訓練や防災訓練により、洪水時にどう行動すればよいかを理解している住民が増えています。洪水による被害を軽減しやすい状態になってきました。',
  },

  // 農業R&D
  rnd_started: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '農業R&Dを始めました',
    body:
      '高温に強い品種や栽培方法の研究開発が始まりました。効果が出るまでには時間がかかりますが、将来の農作物生産を支える対策になります。',
  },
  rnd_tolerance_improved: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '高温耐性品種・栽培技術の効果が出ています',
    body:
      '高温に強い品種や栽培方法の導入が進み、気温上昇による農作物生産への悪影響を抑えやすくなっています。',
  },
  rnd_tolerance_improved_N: {
    color: '#8c6b1a',
    subtitle: 'AGRICULTURE',
    title: '高温耐性品種・栽培技術の効果が出ています',
    body:
      '高温に強い品種や栽培方法の導入が進み、気温上昇による農作物生産への悪影響を抑えやすくなっています。',
  },

  // 予算
  budget_low: {
    color: '#7a5a8c',
    subtitle: 'BUDGET',
    title: '政策に使える予算が少なくなっています',
    body: event =>
      `人口減少、復旧費、移転後のインフラ維持費などの影響により、利用可能な政策ポイントが約${formatOneDecimal(event.value)}ポイントまで低下しました。次の対策に十分な投資がしにくくなっています。`,
  },
  budget_critical: {
    color: '#7a5a8c',
    subtitle: 'BUDGET',
    title: '政策に使える予算が大きく減っています',
    body: event =>
      `人口減少、復旧費、移転後のインフラ維持費などの影響により、利用可能な政策ポイントが約${formatOneDecimal(event.value)}ポイントまで低下しました。次の対策に十分な投資がしにくくなっています。`,
  },
  migration_budget_pressure: {
    color: '#7a5a8c',
    subtitle: 'BUDGET',
    title: '住宅移転により予算負担が増えています',
    body:
      '住宅移転が進んだことで、安全な地域での公共インフラ整備や維持管理に追加費用がかかっています。洪水被害の軽減と、長期的な財政負担のバランスを考える必要があります。',
  },

  // レポート・その他
  report: {
    color: '#3d6b8f',
    subtitle: 'REPORT',
    title: 'シミュレーション内で重要な変化が発生しました',
    body: event => event.message || 'シミュレーション内で重要な変化が発生しました。',
  },
}

export default function ConsequencePage({ sim, onDismiss }) {
  const { t } = useTranslation()
  const currentEvent = sim.gameState.pendingEvents?.[0] ?? {}

  const eventId = resolveEventId(currentEvent)
  const view = EVENT_VIEW_BY_ID[eventId]
  const image = EVENT_IMAGE_BY_ID[eventId]
  const body =
    typeof view.body === 'function'
      ? view.body(currentEvent)
      : view.body

  return (
    <div className={s.page} style={{ '--event-color': view.color }}>
      <div className={s.card}>
        <img
          src={image}
          alt=""
          className={s.eventImage}
        />

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

          <h1 className={s.title}>{currentEvent.title ?? view.title}</h1>
          <p className={s.body}>{currentEvent.message ?? body}</p>

          <button className={s.continueBtn} onClick={onDismiss}>
            {t('consequence.continue')}
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * イベントID解決
 *
 * ここでは「画像を推測」しない。
 * あくまで、年付き・段階付きで送られてくるIDを、
 * 手作業で用意した代表IDに正規化するだけ。
 */
function resolveEventId(event = {}) {
  const rawId = String(event.id ?? event.key ?? 'report')

  console.log('[ConsequencePage] raw event:', event)
  console.log('[ConsequencePage] rawId:', rawId)

  if (EVENT_IMAGE_BY_ID[rawId] && EVENT_VIEW_BY_ID[rawId]) {
    return rawId
  }

  const normalizedId = CANONICAL_EVENT_ID_BY_PATTERN.find(({ pattern }) =>
    pattern.test(rawId)
  )?.id

  if (normalizedId && EVENT_IMAGE_BY_ID[normalizedId] && EVENT_VIEW_BY_ID[normalizedId]) {
    return normalizedId
  }

  console.warn('[ConsequencePage] Unknown event id:', rawId, event)
  return 'report'
}

const CANONICAL_EVENT_ID_BY_PATTERN = [
  { pattern: /^flood_damage_\d+$/, id: 'flood_damage_N' },
  { pattern: /^major_flood_damage_\d+$/, id: 'major_flood_damage_N' },
  { pattern: /^large_flood_damage_\d+$/, id: 'large_flood_damage_N' },
  { pattern: /^severe_flood_damage_\d+$/, id: 'severe_flood_damage_N' },

  { pattern: /^house_migration_step_\d+(point)?$/, id: 'house_migration_step_N' },
  { pattern: /^levee_20mm_step_\d+$/, id: 'levee_20mm_step_N' },
  { pattern: /^rnd_tolerance_improved_\d+$/, id: 'rnd_tolerance_improved_N' },

  {
    pattern: /^resident_capacity_low_turn\d+_summary$/,
    id: 'resident_capacity_low',
  },
  {
    pattern: /^high_risk_houses_unmanaged_turn\d+_summary$/,
    id: 'high_risk_low',
  },
]

function floodDiffText(event) {
  const currentDamage = toNumber(event.value)
  const diff = toNumber(event.diffFromBaseline)
  const baseline = toNumber(event.baselineValue)
  const reduction = diff > 0 ? diff : baseline > currentDamage ? baseline - currentDamage : 0

  if (reduction > 0) {
    return `何も対策をしていなかった場合と比べて${formatJpy(reduction)}分の被害を抑えられました。`
  }

  return ''
}

function gainText(event, unit) {
  const diff = toNumber(event.diffFromBaseline)

  if (diff > 0) {
    return `何も対策をしていなかった場合と比べて約${formatNumber(diff)}${unit}高く保たれています。`
  }

  return ''
}

function migrationBody(event, nearCap) {
  const houses = migrationHouses(event)

  if (nearCap) {
    return houses
      ? `高リスク地域からの移転が大きく進み、これまでに約${houses}戸の住宅が移転しました。移転可能な住宅は少なくなっており、追加投資では効果の伸びが小さくなっていきます。`
      : '高リスク地域からの移転が大きく進みました。移転可能な住宅は少なくなっており、追加投資では効果の伸びが小さくなっていきます。'
  }

  return houses
    ? `洪水リスクの高い地域から、より安全な地域への移転が進んでいます。これまでに約${houses}戸の住宅が移転し、洪水時の住宅被害リスクが下がっています。`
    : '洪水リスクの高い地域から、より安全な地域への移転が進んでいます。洪水時の住宅被害リスクが下がっています。'
}

function migrationHouses(event) {
  const candidates = [
    event.cumulativeMigratedHouses,
    event.cumulative_migrated_houses,
    event.value,
  ]

  const count = candidates
    .map(toNumber)
    .find(value => Number.isFinite(value) && value > 0)

  return count ? formatNumber(count) : ''
}

function formatJpy(value) {
  const amount = toNumber(value)

  if (amount >= 100_000_000) {
    return `約${formatOneDecimal(amount / 100_000_000)}億円`
  }

  if (amount >= 10_000) {
    return `約${Math.round(amount / 10_000).toLocaleString()}万円`
  }

  return `約${Math.round(amount).toLocaleString()}円`
}

function formatNumber(value) {
  return Math.round(toNumber(value)).toLocaleString()
}

function formatOneDecimal(value) {
  return toNumber(value).toFixed(1)
}

function toNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}