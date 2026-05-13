import React, { useState } from 'react'
import PolicySlider from './PolicySlider.jsx'
import { POLICIES } from '../../data/policyEffects.js'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './DecisionPanel.module.css'

export default function DecisionPanel({ mode, sliders, onSliderChange, onPreviewPolicy, onAdvance, loading, year }) {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)
  const policies = POLICIES[mode] ?? POLICIES.upstream
  const isTeam = mode === 'team'
  const nextYear = year + 25

  return (
    <div className={`${s.panel} ${isTeam ? s.teamPanel : ''} ${collapsed ? s.collapsed : ''}`}>
      <button
        className={s.handle}
        onClick={() => setCollapsed(c => !c)}
        title={collapsed ? t('decision.expand') : t('decision.collapse')}
      >
        <span className={s.handleLine} />
        {collapsed && <span className={s.handleLabel}>{t('decision.title')}</span>}
        <span className={s.handleArrow}>{collapsed ? '↑' : '↓'}</span>
        <span className={s.handleLine} />
      </button>

      <div className={s.inner}>
        <div className={s.header}>
          <span className={s.title}>{t('decision.title')}</span>
          <span className={s.subtitle}>{t('decision.sub')} — {year}–{nextYear}</span>
        </div>

        <div className={`${s.policies} ${isTeam ? s.policiesGrid : ''}`}>
          {policies.map(policy => (
            <PolicySlider
              key={policy.key}
              policy={policy}
              value={sliders[policy.key] ?? 5}
              onChange={val => onSliderChange(policy.key, val)}
              onPreview={onPreviewPolicy}
            />
          ))}
        </div>

        <div className={s.advanceArea}>
          <button className={s.advanceBtn} onClick={onAdvance} disabled={loading}>
            {loading ? t('decision.loading') : t('decision.advance')}
          </button>
        </div>
      </div>
    </div>
  )
}
