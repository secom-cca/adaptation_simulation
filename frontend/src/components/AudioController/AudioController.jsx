import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { emit } from '../../logging/operationLog.js'
import { gameAudio, isPositiveEvent, sceneForPhase } from '../../audio/gameAudio.js'
import s from './AudioController.module.css'

export default function AudioController({ phase, event }) {
  const { t } = useTranslation()
  const [audioState, setAudioState] = useState(gameAudio.snapshot())
  const previousPhase = useRef(phase)
  const previousEventId = useRef(null)

  useEffect(() => gameAudio.subscribe(setAudioState), [])

  useEffect(() => {
    const unlock = () => gameAudio.unlock()
    const click = clickEvent => {
      const button = clickEvent.target.closest?.('button, [role="button"]')
      if (button && !button.closest('[data-audio-control]')) gameAudio.playCue('click')
    }
    const visibility = () => gameAudio.suspendForVisibility(document.hidden)

    window.addEventListener('pointerdown', unlock, { passive: true })
    window.addEventListener('keydown', unlock)
    document.addEventListener('click', click)
    document.addEventListener('visibilitychange', visibility)
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      document.removeEventListener('click', click)
      document.removeEventListener('visibilitychange', visibility)
    }
  }, [])

  useEffect(() => {
    gameAudio.setScene(sceneForPhase(phase, event))
    if (previousPhase.current !== phase) {
      if (phase === 'completion' || phase === 'ending') gameAudio.playCue('complete')
      else if (phase !== 'consequence') gameAudio.playCue('transition')
      previousPhase.current = phase
    }
  }, [phase, event])

  useEffect(() => {
    if (phase !== 'consequence') {
      previousEventId.current = null
      return
    }
    const eventId = String(event?.id ?? event?.key ?? `${event?.category}-${event?.year}`)
    if (eventId && eventId !== previousEventId.current) {
      gameAudio.playCue(isPositiveEvent(event) ? 'positive' : 'danger')
      previousEventId.current = eventId
    }
  }, [phase, event])

  const toggle = () => {
    const nextMuted = !audioState.muted
    gameAudio.setMuted(nextMuted)
    if (!nextMuted) gameAudio.playCue('positive')
    emit('audio_toggle', { enabled: !nextMuted }, { source: 'user' })
  }

  const enabled = !audioState.muted
  return (
    <div className={s.control} data-audio-control>
      <button
        type="button"
        className={`${s.button} ${enabled ? s.enabled : ''}`}
        onClick={toggle}
        aria-label={enabled ? t('audio.mute') : t('audio.unmute')}
        aria-pressed={enabled}
        title={enabled ? t('audio.mute') : t('audio.unmute')}
      >
        <span className={s.icon} aria-hidden="true">♪</span>
        <span className={s.label}>{enabled ? t('audio.on') : t('audio.off')}</span>
        <span className={s.meter} aria-hidden="true"><i /><i /><i /></span>
      </button>
    </div>
  )
}
