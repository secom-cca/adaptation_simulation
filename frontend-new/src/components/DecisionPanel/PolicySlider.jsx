import React, { useRef } from 'react'
import { POLICY_EFFECTS, getTier } from '../../data/policyEffects.js'
import { POLICY_MANA_RULES } from '../../data/budget.js'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './PolicySlider.module.css'

export default function PolicySlider({ policy, value, onChange, cumulativeStats, onPreview }) {
  const { lang } = useTranslation()
  const tier = getTier(value)
  const effects = POLICY_EFFECTS[policy.key]?.[tier] ?? []
  const rule = POLICY_MANA_RULES[policy.key] ?? {}
  const stat = cumulativeStats?.find(item => item.key === policy.key)
  const cumulativeUsed = stat?.used ?? 0
  const remainingCap = rule.cumulativeCap == null
    ? null
    : Math.max(0, rule.cumulativeCap - cumulativeUsed + (Number(value) || 0))
  const max = Math.max(0, Math.min(rule.maxPerTurn ?? 10, remainingCap ?? 10))
  const hasStrictCap = rule.maxPerTurn != null || rule.cumulativeCap != null
  const isLevee = policy.key === 'dam_levee_construction_cost'
  const wrapRef = useRef(null)

  const showPreview = () => {
    const rect = wrapRef.current?.getBoundingClientRect()
    onPreview?.(policy.key, rect)
  }

  const hidePreview = () => {
    onPreview?.(null)
  }

  return (
    <div
      ref={wrapRef}
      className={s.wrap}
      onMouseLeave={hidePreview}
      onPointerUp={hidePreview}
      onPointerCancel={hidePreview}
    >
      <div className={s.header}>
        <span className={s.icon}>
          {policy.iconFile ? (
            <img src={`/causal-explorer-assets/${policy.iconFile}`} alt="" aria-hidden="true" />
          ) : policy.icon}
        </span>
        <div className={s.info}>
          <div className={s.label}>{lang === 'ja' ? policy.label.ja : policy.label.en}</div>
          <div className={s.desc}>{lang === 'ja' ? policy.description.ja : policy.description.en}</div>
        </div>
        <div className={`${s.tierBadge} ${s[tier]}`}>{value}</div>
      </div>

      <div className={s.sliderWrap}>
        <div className={s.track}>
          <div className={s.zone} style={{ width: '30%', background: 'rgba(180,80,80,0.08)' }} />
          <div className={s.zone} style={{ width: '40%', background: 'rgba(60,120,180,0.06)' }} />
          <div className={s.zone} style={{ width: '30%', background: 'rgba(60,160,80,0.08)' }} />
        </div>
        <input
          type="range"
          min={0}
          max={max}
          step={1}
          value={Math.min(value, max)}
          className={s.slider}
          onPointerDown={showPreview}
          onFocus={showPreview}
          onBlur={hidePreview}
          onChange={e => {
            showPreview()
            onChange(Number(e.target.value))
          }}
        />
        <div className={s.tickLabels}>
          <span>0</span>
          {isLevee && <span className={s.hardCap}>{lang === 'ja' ? '最低5' : 'min 5'}</span>}
          <span className={hasStrictCap ? s.hardCap : ''}>
            {hasStrictCap
              ? (rule.cumulativeCap != null
                  ? (lang === 'ja' ? `${max} (累積上限 ${rule.cumulativeCap})` : `${max} (cap ${rule.cumulativeCap})`)
                  : (lang === 'ja' ? `${max} (1ターン上限 ${rule.maxPerTurn})` : `${max} (turn cap ${rule.maxPerTurn})`))
              : (lang === 'ja' ? '予算内' : 'within budget')}
          </span>
        </div>
      </div>

      {stat?.cap != null && (
        <div className={s.ruleLine}>
          <strong>{lang === 'ja' ? `累積 ${stat.used}/${stat.cap}` : `cum. ${stat.used}/${stat.cap}`}</strong>
        </div>
      )}

      {effects.length > 0 && (
        <ul className={s.effectsList}>
          {effects.slice(0, 2).map((e, i) => (
            <li key={i} className={s.effectItem}>
              <span className={e.positive ? s.arrowUp : s.arrowDown}>
                {e.positive ? '+' : '-'}
              </span>
              <span className={s.effectText}>
                {lang === 'ja' ? e.text.ja : e.text.en}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
