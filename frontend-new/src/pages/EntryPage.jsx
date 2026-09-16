import React, { useEffect, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { getResearchEthics } from '../data/researchEthics.js'
import {
  beginEntryLogging,
  emit,
  setLogContext,
} from '../logging/operationLog.js'
import s from './EntryPage.module.css'

export default function EntryPage({ onStart, onEthicsEvent }) {
  const { t, lang, toggle } = useTranslation()
  const ethics = getResearchEthics(lang)
  const [userName, setUserName] = useState('')
  const [teamName, setTeamName] = useState('')
  const [mode, setMode] = useState('team')
  const [rcpValue, setRcpValue] = useState('composite')
  const [ethicsConsent, setEthicsConsent] = useState(false)
  const [ethicsConsentAt, setEthicsConsentAt] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)

  useEffect(() => {
    beginEntryLogging()
    setLogContext({ phase: 'entry', cycle: null, year: null, gameView: null })
  }, [])

  const canStart = userName.trim().length > 0 && ethicsConsent

  const modes = [
    { value: 'upstream',   nameKey: 'entry.upstream.name', descKey: 'entry.upstream.desc' },
    { value: 'downstream', nameKey: 'entry.downstream.name', descKey: 'entry.downstream.desc' },
    { value: 'team',       nameKey: 'entry.team.name', descKey: 'entry.team.desc' },
  ]
  const scenarios = [
    { value: 1.9, label: 'RCP1.9', desc: lang === 'ja' ? '強い緩和' : 'Strong mitigation' },
    { value: 4.5, label: 'RCP4.5', desc: lang === 'ja' ? '中間' : 'Intermediate' },
    { value: 8.5, label: 'RCP8.5', desc: lang === 'ja' ? '非常に高い排出' : 'Very high emissions' },
    { value: 'composite', label: lang === 'ja' ? '複合シナリオ' : 'Composite', desc: lang === 'ja' ? '3つのRCPを比較表示' : 'Compare three RCPs' },
  ]

  function handleConsentChange(checked) {
    setEthicsConsent(checked)
    if (checked) {
      const at = new Date().toISOString()
      setEthicsConsentAt(at)
      emit('ethics_consent_checked', { label_key: 'entry.ethics.consent' })
      onEthicsEvent?.('ethics_consent_checked')
    } else {
      setEthicsConsentAt(null)
      emit('ethics_consent_unchecked', { label_key: 'entry.ethics.consent' })
      onEthicsEvent?.('ethics_consent_unchecked')
    }
  }

  function openDetail() {
    setDetailOpen(true)
    emit('ethics_detail_opened', {})
  }

  function closeDetail(via) {
    setDetailOpen(false)
    emit('ethics_detail_closed', { via })
  }

  function handleStart() {
    if (!canStart) return
    onStart({
      userName: userName.trim(),
      teamName: teamName.trim(),
      mode,
      rcpValue,
      ethicsConsent: true,
      ethicsConsentAt: ethicsConsentAt || new Date().toISOString(),
    })
  }

  return (
    <div className={s.page}>
      <div className={s.card}>
        <div className={s.titleRow}>
          <h1 className={s.title}>River Basin<br />Adaptation Game</h1>
          <button
            className={s.langBtn}
            onClick={() => {
              const from = lang
              toggle()
              emit('language_toggle', { from, to: from === 'ja' ? 'en' : 'ja' })
            }}
          >
            {lang === 'ja' ? 'EN' : '日本語'}
          </button>
        </div>
        <p className={s.subtitle}>{t('entry.subtitle')}</p>

        <div className={s.fields}>
          <label className={s.label}>
            {t('entry.username')}
            <input
              className={s.input}
              value={userName}
              onChange={e => setUserName(e.target.value)}
              placeholder={t('entry.username.ph')}
              maxLength={20}
            />
          </label>

          <label className={s.label}>
            {t('entry.team')}
            <input
              className={s.input}
              value={teamName}
              onChange={e => setTeamName(e.target.value)}
              placeholder={t('entry.team.ph')}
              maxLength={30}
            />
          </label>

          <fieldset className={s.fieldset}>
            <legend className={s.legend}>{t('entry.mode.label')}</legend>
            <div className={s.modeRow}>
              {modes.map(m => (
                <button
                  key={m.value}
                  className={`${s.modeBtn} ${mode === m.value ? s.selected : ''}`}
                  onClick={() => setMode(m.value)}
                  type="button"
                >
                  <span className={s.modeName}>{t(m.nameKey)}</span>
                  <span className={s.modeDesc}>{t(m.descKey)}</span>
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className={s.fieldset}>
            <legend className={s.legend}>{t('entry.rcp.label')}</legend>
            <div className={s.rcpRow}>
              {scenarios.map(item => (
                <button key={item.value} type="button" className={`${s.rcpBtn} ${rcpValue === item.value ? s.selected : ''}`} onClick={() => setRcpValue(item.value)}>
                  <span className={s.rcpLabel}>{item.label}</span>
                  <span className={s.rcpDesc}>{item.desc}</span>
                </button>
              ))}
            </div>
          </fieldset>

        </div>

        <div className={s.ethicsRow}>
          <label className={s.ethicsLabel}>
            <input
              type="checkbox"
              className={s.ethicsCheckbox}
              checked={ethicsConsent}
              onChange={e => handleConsentChange(e.target.checked)}
            />
            <span>{ethics.consentLabel}</span>
          </label>
          <button type="button" className={s.ethicsDetailBtn} onClick={openDetail}>
            {ethics.detailLink}
          </button>
        </div>

        <button
          className={s.startBtn}
          onClick={handleStart}
          disabled={!canStart}
        >
          {t('entry.start')}
        </button>
      </div>

      {detailOpen && (
        <div
          className={s.modalOverlay}
          onClick={() => closeDetail('overlay')}
          role="presentation"
        >
          <div
            className={s.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="ethics-modal-title"
            onClick={e => e.stopPropagation()}
          >
            <h2 id="ethics-modal-title" className={s.modalTitle}>
              {ethics.modalTitle}
            </h2>
            <div className={s.modalBody}>
              {ethics.sections.map(section => (
                <section key={section.heading} className={s.modalSection}>
                  <h3>{section.heading}</h3>
                  <p>{section.body}</p>
                </section>
              ))}
            </div>
            <button
              type="button"
              className={s.modalClose}
              onClick={() => closeDetail('close_button')}
            >
              {ethics.close}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
