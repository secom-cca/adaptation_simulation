import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './TopBar.module.css'

export default function TopBar({ year, cycle, mode, goal, view, onSetView, hasNewResults }) {
  const { t, lang, toggle } = useTranslation()

  return (
    <div className={s.bar}>
      <div className={s.left}>
        <span className={s.year}>YEAR {year}</span>
        <span className={s.dot} />
        <span className={s.cycle}>CYCLE {cycle} / 3</span>
        <span className={s.separator} />
        <span className={s.mode}>{t(`topbar.${mode}`)}</span>
      </div>

      <div className={s.center}>
        <span className={s.goal}>{goal}</span>
      </div>

      <div className={s.right}>
        <div className={s.tabs}>
          {['simple', 'detail', 'analysis'].map(v => (
            <button
              key={v}
              className={`${s.tab} ${view === v ? s.tabActive : ''}`}
              onClick={() => onSetView(v)}
            >
              {t(`topbar.${v}`)}
              {v === 'simple' && hasNewResults && <span className={s.newDot} />}
            </button>
          ))}
        </div>

        <button className={s.langBtn} onClick={toggle}>
          {lang === 'ja' ? 'EN' : '日本語'}
        </button>
      </div>
    </div>
  )
}
