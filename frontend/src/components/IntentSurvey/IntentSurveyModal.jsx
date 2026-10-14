import React, { useMemo, useState } from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import {
  INTENT_OBJECTIVE_OPTIONS,
  emptyIntentSurveyAnswers,
  isIntentSurveyComplete,
} from '../../data/intentSurveyQuestions.js'
import s from './IntentSurveyModal.module.css'

function optionLabel(opt, lang) {
  return lang === 'ja' ? opt.label.ja : opt.label.en
}

export default function IntentSurveyModal({
  cycle = 1,
  year = 2026,
  submitted = false,
  simulationReady = false,
  onSubmit,
  onBack,
}) {
  const { lang } = useTranslation()
  const [answers, setAnswers] = useState(() => emptyIntentSurveyAnswers())
  const [error, setError] = useState('')

  const complete = useMemo(() => isIntentSurveyComplete(answers), [answers])

  function toggleObjective(value) {
    setAnswers(prev => {
      const cur = Array.isArray(prev.target_objectives) ? prev.target_objectives : []
      const next = cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]
      return { ...prev, target_objectives: next }
    })
    setError('')
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!complete) {
      setError(lang === 'ja' ? '当てはまるものを1つ以上選んでください。' : 'Please select at least one option.')
      return
    }
    onSubmit?.(answers)
  }

  if (submitted) {
    return (
      <div className={s.overlay} role="dialog" aria-modal="true" aria-labelledby="intent-survey-waiting-title">
        <div className={s.card}>
          <div className={s.waiting}>
            {!simulationReady && <div className={s.spinner} aria-hidden="true" />}
            <p className={s.eyebrow}>{lang === 'ja' ? '約30秒' : 'About 30 sec'}</p>
            <h2 id="intent-survey-waiting-title" className={s.waitingTitle}>
              {simulationReady
                ? (lang === 'ja' ? '結果を表示します…' : 'Showing results…')
                : (lang === 'ja' ? '回答を受け付けました' : 'Thanks — answers received')}
            </h2>
            <p className={s.waitingText}>
              {simulationReady
                ? (lang === 'ja' ? '次の画面へ進みます。' : 'Moving to the next screen.')
                : (lang === 'ja'
                  ? '裏でシミュレーションを計算しています。しばらくお待ちください。'
                  : 'The simulation is still running in the background. Please wait a moment.')}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={s.overlay} role="dialog" aria-modal="true" aria-labelledby="intent-survey-title">
      <form className={s.card} onSubmit={handleSubmit}>
        <header>
          <p className={s.eyebrow}>{lang === 'ja' ? '約30秒' : 'About 30 sec'}</p>
          <h2 id="intent-survey-title" className={s.title}>
            {lang === 'ja' ? '今回の選択の意図' : 'Intent of this decision'}
          </h2>
          <p className={s.lede}>
            {lang === 'ja'
              ? `第${cycle}ターン（${year}〜${year + 24}年）の政策配分について、どの指標を上げたいと思って選びましたか？（複数選択可）`
              : `For turn ${cycle} (${year}–${year + 24}), which indicators were you trying to improve? (Select all that apply.)`}
          </p>
        </header>

        <fieldset className={s.block}>
          <legend className={s.legend}>
            {lang === 'ja' ? '上げたいと思った指標（目的）' : 'Objectives you wanted to improve'}
            <span className={s.req}>*</span>
          </legend>
          <div className={s.options}>
            {INTENT_OBJECTIVE_OPTIONS.map(opt => (
              <label key={opt.value} className={s.option}>
                <input
                  type="checkbox"
                  name="target_objectives"
                  value={opt.value}
                  checked={answers.target_objectives.includes(opt.value)}
                  onChange={() => toggleObjective(opt.value)}
                />
                <span>{optionLabel(opt, lang)}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className={s.block}>
          <legend className={s.legend}>
            {lang === 'ja' ? '補足（任意）' : 'Anything else? (optional)'}
          </legend>
          <textarea
            className={s.textarea}
            value={answers.free_text}
            maxLength={400}
            rows={3}
            placeholder={lang === 'ja' ? 'なぜそう選んだかなど、自由に書いてください' : 'Optional: why you chose this way'}
            onChange={e => setAnswers(prev => ({ ...prev, free_text: e.target.value }))}
          />
        </fieldset>

        {error && <p className={s.error}>{error}</p>}

        <div className={s.actions}>
          <button type="button" className={s.secondary} onClick={() => onBack?.()}>
            {lang === 'ja' ? '戻る' : 'Back'}
          </button>
          <button type="submit" className={s.primary} disabled={!complete}>
            {lang === 'ja' ? '回答して進む' : 'Submit and continue'}
          </button>
        </div>
      </form>
    </div>
  )
}
