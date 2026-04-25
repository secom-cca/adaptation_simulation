import React from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './ConsequencePage.module.css'

const EVENT_META = {
  // consequence events
  flood:            { color: '#3d6b8f', image: '/events/flood.png',             subtitleKey: 'event.flood.subtitle',   titleKey: 'event.flood.title',   bodyKey: 'event.flood.body'   },
  drought:          { color: '#8c6b1a', image: '/events/drought.png',           subtitleKey: 'event.drought.subtitle', titleKey: 'event.drought.title', bodyKey: 'event.drought.body' },
  water_quality:    { color: '#4a7a3a', image: '/events/water_quality.png',     subtitleKey: 'event.wq.subtitle',      titleKey: 'event.wq.title',      bodyKey: 'event.wq.body'      },
  landslide:        { color: '#6b4a3a', image: '/events/landslide.png',         subtitleKey: 'event.ls.subtitle',      titleKey: 'event.ls.title',      bodyKey: 'event.ls.body'      },
  // exogenous events
  wildfire:         { color: '#b85c2a', image: '/events/wildfire.png',          subtitleKey: 'event.wf.subtitle',      titleKey: 'event.wf.title',      bodyKey: 'event.wf.body'      },
  tech_breakthrough:{ color: '#2a7a5a', image: '/events/tech_breakthrough.png', subtitleKey: 'event.tb.subtitle',      titleKey: 'event.tb.title',      bodyKey: 'event.tb.body'      },
}

export default function ConsequencePage({ sim, onDismiss }) {
  const { t } = useTranslation()
  const { pendingEvents, year } = sim.gameState
  const currentEvent = pendingEvents?.[0]
  const ev = EVENT_META[currentEvent?.key] ?? EVENT_META.flood
  const isExogenous = currentEvent?.type === 'exogenous'

  return (
    <div className={s.page} style={{ '--event-color': ev.color }}>
      <div className={s.card}>

        {/* ── Event image ── */}
        <img src={ev.image} alt="" className={s.eventImage} />

        {/* ── Text content ── */}
        <div className={s.content}>
          <div className={s.meta}>
            <span className={s.yearTag}>YEAR {year - 1}</span>
            {isExogenous && <span className={s.tag}>{t('event.tag.random')}</span>}
            <span className={s.subtitle}>{t(ev.subtitleKey)}</span>
          </div>
          <h1 className={s.title}>{t(ev.titleKey)}</h1>
          <p className={s.body}>{t(ev.bodyKey)}</p>
          <button className={s.continueBtn} onClick={onDismiss}>
            {t('consequence.continue')}
          </button>
        </div>

      </div>
    </div>
  )
}
