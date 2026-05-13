import React, { useRef } from 'react'
import { POLICY_EFFECTS, getTier } from '../../data/policyEffects.js'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './PolicySlider.module.css'

export default function PolicySlider({ policy, value, onChange, onPreview }) {
  const { t, lang } = useTranslation()
  const tier = getTier(value)
  const effects = POLICY_EFFECTS[policy.key]?.[tier] ?? []
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
        <span className={s.icon}>{policy.icon}</span>
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
          type="range" min={0} max={10} step={1} value={value}
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
          <span>{t('tier.weak')} 0</span>
          <span>{t('tier.standard')} 5</span>
          <span>{t('tier.strong')} 10</span>
        </div>
      </div>

      {effects.length > 0 && (
        <ul className={s.effectsList}>
          {effects.slice(0, 3).map((e, i) => (
            <li key={i} className={s.effectItem}>
              <span className={e.positive ? s.arrowUp : s.arrowDown}>
                {e.positive ? '▲' : '▼'}
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
