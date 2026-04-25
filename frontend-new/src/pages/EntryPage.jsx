import React, { useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './EntryPage.module.css'

const RCP_OPTIONS = [1.9, 2.6, 4.5, 6.0, 8.5]

export default function EntryPage({ onStart }) {
  const { t, lang, toggle } = useTranslation()
  const [userName, setUserName] = useState('')
  const [teamName, setTeamName] = useState('')
  const [mode, setMode] = useState('team')
  const [rcp, setRcp] = useState(4.5)

  const canStart = userName.trim().length > 0

  const modes = [
    { value: 'upstream',   nameKey: 'entry.upstream.name', descKey: 'entry.upstream.desc' },
    { value: 'downstream', nameKey: 'entry.downstream.name', descKey: 'entry.downstream.desc' },
    { value: 'team',       nameKey: 'entry.team.name', descKey: 'entry.team.desc' },
  ]

  return (
    <div className={s.page}>
      <div className={s.card}>
        <div className={s.titleRow}>
          <h1 className={s.title}>River Basin<br />Adaptation Game</h1>
          <button className={s.langBtn} onClick={toggle}>
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
              {RCP_OPTIONS.map(r => (
                <button
                  key={r}
                  className={`${s.rcpBtn} ${rcp === r ? s.selected : ''}`}
                  onClick={() => setRcp(r)}
                  type="button"
                >
                  <span className={s.rcpLabel}>RCP {r}</span>
                  <span className={s.rcpDesc}>{t(`rcp.${r}.desc`)}</span>
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <button
          className={s.startBtn}
          onClick={() => onStart({ userName: userName.trim(), teamName: teamName.trim(), mode, rcpValue: rcp })}
          disabled={!canStart}
        >
          {t('entry.start')}
        </button>
      </div>
    </div>
  )
}
