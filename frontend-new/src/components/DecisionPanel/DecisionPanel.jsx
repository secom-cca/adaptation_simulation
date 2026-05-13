import React, { useState } from 'react'
import PolicySlider from './PolicySlider.jsx'
import { POLICIES } from '../../data/policyEffects.js'
import { getCumulativePolicyStats } from '../../data/budget.js'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './DecisionPanel.module.css'

export default function DecisionPanel({
  mode,
  sliders,
  onSliderChange,
  onPreviewPolicy,
  onAdvance,
  loading,
  year,
  policyHistory = [],
  budgetRow,
}) {
  const { t, lang } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)
  const policies = POLICIES[mode] ?? POLICIES.upstream
  const isTeam = mode === 'team'
  const nextYear = year + 25
  const cumulativeStats = getCumulativePolicyStats(policyHistory).filter(item => item.used > 0 || item.cap != null)

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
          <div className={s.heading}>
            <span className={s.title}>{t('decision.title')}</span>
            <span className={s.subtitle}>{t('decision.sub')} - {year}-{nextYear}</span>
          </div>
          <div className={s.headerActions}>
            <div className={s.budgetStrip}>
              <span>{lang === 'ja' ? '使用可能' : 'Available'}</span>
              <strong>{(budgetRow?.availableBudgetPoints ?? 10).toFixed(1)} / 10</strong>
              <span>{lang === 'ja' ? '配分' : 'Used'}</span>
              <strong>{budgetRow?.usedPolicyPoints ?? 0}</strong>
            </div>
            <button className={s.advanceBtn} onClick={onAdvance} disabled={loading}>
              {loading ? t('decision.loading') : t('decision.advance')}
            </button>
          </div>
        </div>

        <div className={`${s.policies} ${isTeam ? s.policiesGrid : ''}`}>
          {policies.map(policy => (
            <PolicySlider
              key={policy.key}
              policy={policy}
              value={sliders[policy.key] ?? 0}
              onChange={val => onSliderChange(policy.key, val)}
              cumulativeStats={cumulativeStats}
              onPreview={onPreviewPolicy}
            />
          ))}
        </div>

        <div className={s.footer}>
          {cumulativeStats.length > 0 && (
            <div className={s.cumulativeBox}>
              <span className={s.cumulativeTitle}>{lang === 'ja' ? '累計上限' : 'Cumulative caps'}</span>
              <div className={s.cumulativeItems}>
                {cumulativeStats.map(item => (
                  <span key={item.key} className={s.cumulativeChip}>
                    <span>{lang === 'ja' ? item.labelJa : item.labelEn}</span>
                    <strong>{item.used}{item.cap != null ? ` / ${item.cap}` : ''}</strong>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
