import React, { useEffect } from 'react'
import { emit, setLogContext } from '../logging/operationLog.js'
import s from './CompletionPage.module.css'

const SPARKS = Array.from({ length: 18 }, (_, index) => index)

export default function CompletionPage({ onContinue }) {
  useEffect(() => {
    setLogContext({ phase: 'completion', cycle: 4, year: 2101 })
    emit('game_completion_shown', { final_year: 2100, cycles_completed: 3 }, { source: 'system' })
  }, [])

  return (
    <main className={s.page} aria-labelledby="completion-title">
      <div className={s.glow} aria-hidden="true" />
      <div className={s.sparks} aria-hidden="true">
        {SPARKS.map(index => <span key={index} style={{ '--spark': index }} />)}
      </div>

      <section className={s.card}>
        <div className={s.check} aria-hidden="true">
          <svg viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="27" />
            <path d="M19 33.5 28 42l18-21" />
          </svg>
        </div>
        <p className={s.kicker}>SIMULATION COMPLETE</p>
        <h1 id="completion-title">2100年までの政策決定が<br />完了しました</h1>
        <p className={s.lead}>3つのターンを終えました。あなたの選択が流域の未来に与えた結果を確認しましょう。</p>

        <div className={s.timeline} aria-label="全3ターン完了">
          {[2050, 2075, 2100].map((year, index) => (
            <React.Fragment key={year}>
              {index > 0 && <span className={s.line} aria-hidden="true" />}
              <div className={s.milestone}>
                <span aria-hidden="true">✓</span>
                <strong>{year}</strong>
                <small>第{index + 1}ターン</small>
              </div>
            </React.Fragment>
          ))}
        </div>

        <button type="button" className={s.continueButton} onClick={onContinue} autoFocus>
          最終結果を見る
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </main>
  )
}
