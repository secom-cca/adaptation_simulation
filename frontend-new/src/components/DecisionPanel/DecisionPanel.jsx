import React, { useEffect, useMemo, useState, useCallback } from 'react'
import PolicySlider from './PolicySlider.jsx'
import ImageLightbox from '../ImageLightbox/ImageLightbox.jsx'
import { POLICIES } from '../../data/policyEffects.js'
import { getCumulativePolicyStats } from '../../data/budget.js'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './DecisionPanel.module.css'

export default function DecisionPanel({
  mode,
  sliders,
  onSliderChange,
  onPolicySelect,
  onAdvance,
  loading,
  year,
  policyHistory = [],
  budgetRow,
}) {
  const { t, lang } = useTranslation()
  const policies = POLICIES[mode] ?? POLICIES.upstream
  const [activePolicyKey, setActivePolicyKey] = useState(policies[0]?.key)
  const isTeam = mode === 'team'
  const nextYear = year + 24
  const cumulativeStats = getCumulativePolicyStats(policyHistory).filter(item => item.used > 0 || item.cap != null)
  const availablePoints = Math.round(budgetRow?.availableBudgetPoints ?? 10)
  const usedPoints = Math.round(budgetRow?.usedPolicyPoints ?? 0)
  const remainingPoints = Math.max(0, availablePoints - usedPoints)
  const usedGaugeWidth = Math.min(100, Math.max(0, usedPoints * 10))
  const remainingGaugeWidth = Math.min(100 - usedGaugeWidth, Math.max(0, remainingPoints * 10))
  const activePolicy = useMemo(
    () => policies.find(policy => policy.key === activePolicyKey) ?? policies[0],
    [activePolicyKey, policies],
  )
  const [lightbox, setLightbox] = useState(null)
  const closeLightbox = useCallback(() => setLightbox(null), [])
  const policyMapSrc = activePolicy
    ? `/causal-explorer-assets/policy-mini-maps/${lang === 'ja' ? 'ja' : 'en'}/${policyMapFile(activePolicy.key)}`
    : null
  const policyMapAlt = activePolicy
    ? (lang === 'ja'
      ? `${activePolicy.label.ja}が流域に与える影響`
      : `${activePolicy.label.en} impact map`)
    : ''

  useEffect(() => {
    if (!policies.some(policy => policy.key === activePolicyKey)) {
      setActivePolicyKey(policies[0]?.key)
    }
  }, [activePolicyKey, policies])

  const selectPolicy = (key) => {
    setActivePolicyKey(key)
    onPolicySelect?.(key)
  }

  return (
    <div className={`${s.panel} ${isTeam ? s.teamPanel : ''}`}>
      <div className={s.inner}>
        <div className={s.header}>
          <div className={s.heading}>
            <span className={s.title}>{t('decision.title')}</span>
            <span className={s.subtitle}>{t('decision.sub')} - {year}-{nextYear}</span>
          </div>
          <div className={s.headerActions}>
            <div className={s.budgetStrip}>
              <div className={s.budgetTextRow}>
                <span>{lang === 'ja' ? '配分後の残り' : 'Remaining'}</span>
                <strong>{remainingPoints} / 10 {lang === 'ja' ? 'ポイント' : 'points'}</strong>
              </div>
              <div
                className={s.budgetGauge}
                role="meter"
                aria-label={lang === 'ja' ? '配分後に残っているポイント' : 'Points remaining after allocation'}
                aria-valuemin="0"
                aria-valuemax="10"
                aria-valuenow={remainingPoints}
              >
                <span
                  className={s.gaugeUsed}
                  style={{ width: `${usedGaugeWidth}%` }}
                  title={`${lang === 'ja' ? '配分済み' : 'Used'}: ${usedPoints}`}
                />
                <span
                  className={s.gaugeRemaining}
                  style={{ width: `${remainingGaugeWidth}%` }}
                  title={`${lang === 'ja' ? '残り' : 'Remaining'}: ${remainingPoints}`}
                />
              </div>
              <div className={s.budgetLegend}>
                <span className={s.legendUsed}>{lang === 'ja' ? `配分済み ${usedPoints}` : `Used ${usedPoints}`}</span>
                <span className={s.legendRemaining}>{lang === 'ja' ? `使用可能 ${remainingPoints}` : `Available ${remainingPoints}`}</span>
              </div>
            </div>
            <button className={s.advanceBtn} onClick={onAdvance} disabled={loading}>
              {loading ? t('decision.loading') : t('decision.advance')}
            </button>
          </div>
        </div>

        <div className={s.policyTabs} role="tablist" aria-label={lang === 'ja' ? '政策' : 'Policies'}>
          {policies.map(policy => {
            const selected = policy.key === activePolicy?.key
            return (
              <button
                key={policy.key}
                type="button"
                role="tab"
                aria-selected={selected}
                className={`${s.policyTab} ${selected ? s.policyTabActive : ''}`}
                onClick={() => selectPolicy(policy.key)}
              >
                {lang === 'ja' ? policy.label.ja : policy.label.en}
              </button>
            )
          })}
        </div>

        {activePolicy && (
          <div className={s.policyDetail} role="tabpanel">
            <div className={s.sliderPane}>
              <PolicySlider
                policy={activePolicy}
                value={sliders[activePolicy.key] ?? 0}
                onChange={val => onSliderChange(activePolicy.key, val)}
                cumulativeStats={cumulativeStats}
              />
            </div>
            <button
              type="button"
              className={`${s.policyMap} ${s.expandableImage}`}
              aria-label={lang === 'ja' ? '政策影響図を拡大表示' : 'Expand policy impact map'}
              onClick={() => setLightbox({ src: policyMapSrc, alt: policyMapAlt })}
            >
              <img src={policyMapSrc} alt={policyMapAlt} />
            </button>
          </div>
        )}

        <div className={s.footer}>
          {cumulativeStats.length > 0 && (
            <div className={s.cumulativeBox}>
              <span className={s.cumulativeTitle}>{lang === 'ja' ? '累積上限' : 'Cumulative caps'}</span>
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

      <ImageLightbox
        src={lightbox?.src}
        alt={lightbox?.alt}
        onClose={closeLightbox}
      />
    </div>
  )
}

function policyMapFile(key) {
  return {
    planting_trees_amount: 'forest.png',
    dam_levee_construction_cost: 'levee.png',
    paddy_dam_construction_cost: 'paddy-dam.png',
    house_migration_amount: 'relocation.png',
    capacity_building_cost: 'preparedness.png',
    agricultural_RnD_cost: 'agri-rnd.png',
  }[key] ?? 'forest.png'
}
