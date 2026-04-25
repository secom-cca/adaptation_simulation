import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './ScenarioBriefing.module.css'

const DOMAIN_COLORS = {
  Flood: '#3d6b8f', Flooding: '#3d6b8f',
  Agriculture: '#4a8c5c', Ecology: '#6b8c3d',
  Budget: '#8c6b3d', Livelihood: '#7a4a8c',
  洪水: '#3d6b8f', 農業: '#4a8c5c', 生態系: '#6b8c3d',
  予算: '#8c6b3d', 生計: '#7a4a8c',
}

const BRIEFING_DOMAINS = [
  ['Flood', 'Agriculture'],
  ['Agriculture', 'Ecology'],
  ['Flood', 'Budget', 'Livelihood'],
]

export default function ScenarioBriefing({ year, cycle }) {
  const { t } = useTranslation()
  const idx = Math.min(cycle - 1, 2) + 1
  const domains = BRIEFING_DOMAINS[Math.min(cycle - 1, 2)]

  return (
    <div className={s.card}>
      <div className={s.header}>{t('briefing.header')}</div>
      <h3 className={s.title}>{t(`briefing.${idx}.title`)}</h3>
      <p className={s.body}>{t(`briefing.${idx}.body`)}</p>
      <div className={s.domainRow}>
        <span className={s.domainLabel}>{t('briefing.domains.label')}</span>
        <div className={s.tags}>
          {domains.map(d => (
            <span
              key={d}
              className={s.tag}
              style={{ background: `${DOMAIN_COLORS[d] ?? '#888'}22`, color: DOMAIN_COLORS[d] ?? '#888' }}
            >
              {d}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
