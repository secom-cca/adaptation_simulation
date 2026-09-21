import React, { useMemo, useState } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import {
  SURVEY_QUESTIONS,
  emptySurveyAnswers,
  isSurveyComplete,
} from '../data/surveyQuestions.js'
import s from './SurveyPage.module.css'

function optionLabel(opt, lang) {
  return lang === 'ja' ? opt.label.ja : opt.label.en
}

function questionLabel(q, lang) {
  return lang === 'ja' ? q.label.ja : q.label.en
}

export default function SurveyPage({
  onCancel,
  onSubmitAndRestart,
  onSkipAndRestart,
  initialAnswers = null,
  exportSaving = false,
}) {
  const { lang } = useTranslation()
  const [answers, setAnswers] = useState(() => initialAnswers || emptySurveyAnswers())
  const [error, setError] = useState('')
  const [skipConfirmOpen, setSkipConfirmOpen] = useState(false)

  const complete = useMemo(() => isSurveyComplete(answers), [answers])

  function setSingle(id, value) {
    setAnswers(prev => ({ ...prev, [id]: value }))
    setError('')
  }

  function toggleMulti(id, value) {
    setAnswers(prev => {
      const cur = Array.isArray(prev[id]) ? prev[id] : []
      const next = cur.includes(value) ? cur.filter(v => v !== value) : [...cur, value]
      return { ...prev, [id]: next }
    })
    setError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!complete) {
      setError(lang === 'ja' ? '必須項目にすべて回答してください。' : 'Please answer all required questions.')
      return
    }
    await onSubmitAndRestart?.(answers)
  }

  async function confirmSkip() {
    setSkipConfirmOpen(false)
    await onSkipAndRestart?.()
  }

  return (
    <div className={s.page}>
      <div className={s.topBar}>
        <button
          type="button"
          className={s.skipBtn}
          onClick={() => setSkipConfirmOpen(true)}
          disabled={exportSaving}
        >
          {lang === 'ja' ? 'アンケートをスキップする' : 'Skip survey'}
        </button>
      </div>

      <form className={s.card} onSubmit={handleSubmit}>
        <header className={s.header}>
          <p className={s.eyebrow}>{lang === 'ja' ? '約3分' : 'About 3 minutes'}</p>
          <h1 className={s.title}>
            {lang === 'ja' ? '体験後アンケート' : 'Post-experience survey'}
          </h1>
          <p className={s.lede}>
            {lang === 'ja'
              ? '研究のための短いアンケートです。回答送信時に操作ログと一緒に保存されます。'
              : 'A short research survey. Submitting saves the operation log.'}
          </p>
        </header>

        <div className={s.questions}>
          {SURVEY_QUESTIONS.map((q, index) => (
            <fieldset key={q.id} className={s.block}>
              <legend className={s.legend}>
                <span className={s.qIndex}>{index + 1}</span>
                {questionLabel(q, lang)}
                {q.required && <span className={s.req}>*</span>}
              </legend>

              {q.type === 'single' && (
                <div className={s.options}>
                  {q.options.map(opt => (
                    <label key={opt.value} className={s.option}>
                      <input
                        type="radio"
                        name={q.id}
                        value={opt.value}
                        checked={answers[q.id] === opt.value}
                        onChange={() => setSingle(q.id, opt.value)}
                      />
                      <span>{optionLabel(opt, lang)}</span>
                    </label>
                  ))}
                </div>
              )}

              {q.type === 'multi' && (
                <div className={s.options}>
                  {q.options.map(opt => (
                    <label key={opt.value} className={s.option}>
                      <input
                        type="checkbox"
                        name={q.id}
                        value={opt.value}
                        checked={(answers[q.id] || []).includes(opt.value)}
                        onChange={() => toggleMulti(q.id, opt.value)}
                      />
                      <span>{optionLabel(opt, lang)}</span>
                    </label>
                  ))}
                </div>
              )}

              {q.type === 'likert5' && (
                <div className={s.likert}>
                  <div className={s.likertScale}>
                    {[1, 2, 3, 4, 5].map(n => (
                      <label key={n} className={`${s.likertItem} ${answers[q.id] === n ? s.likertActive : ''}`}>
                        <input
                          type="radio"
                          name={q.id}
                          value={n}
                          checked={answers[q.id] === n}
                          onChange={() => setSingle(q.id, n)}
                        />
                        <span>{n}</span>
                      </label>
                    ))}
                  </div>
                  <div className={s.likertEnds}>
                    <span>{lang === 'ja' ? q.likertLabels.ja.low : q.likertLabels.en.low}</span>
                    <span>{lang === 'ja' ? q.likertLabels.ja.high : q.likertLabels.en.high}</span>
                  </div>
                </div>
              )}

              {q.type === 'text' && (
                <textarea
                  className={s.textarea}
                  value={answers[q.id] || ''}
                  maxLength={q.maxLength || 280}
                  rows={3}
                  placeholder={lang === 'ja' ? '任意入力' : 'Optional'}
                  onChange={e => setSingle(q.id, e.target.value)}
                />
              )}
            </fieldset>
          ))}
        </div>

        {error && <p className={s.error}>{error}</p>}

        <div className={s.actions}>
          <button type="button" className={s.secondary} onClick={onCancel} disabled={exportSaving}>
            {lang === 'ja' ? '結果画面に戻る' : 'Back to results'}
          </button>
        </div>

        <div className={s.restartBlock}>
          <button
            type="submit"
            className={s.restartBtn}
            disabled={!complete || exportSaving}
          >
            {exportSaving
              ? (lang === 'ja' ? 'ログ保存中…' : 'Saving log…')
              : (lang === 'ja' ? '回答を送信する' : 'Submit answers')}
          </button>
          <p className={s.restartHint}>
            {lang === 'ja'
              ? '必須項目をすべて回答すると送信できます。送信後、操作ログを保存して終了画面へ進みます。'
              : 'Enabled once all required items are answered. Submitting saves the log and shows the completion screen.'}
          </p>
        </div>
      </form>

      {skipConfirmOpen && (
        <div className={s.modalOverlay} role="dialog" aria-modal="true" aria-labelledby="skip-survey-title">
          <div className={s.modalCard}>
            <h2 id="skip-survey-title" className={s.modalTitle}>
              {lang === 'ja' ? '本当にスキップしますか？' : 'Are you sure you want to skip?'}
            </h2>
            <p className={s.modalText}>
              {lang === 'ja'
                ? 'アンケートをスキップして終了画面へ進みます。操作ログは保存されます。'
                : 'You will proceed to the completion screen. The operation log will still be saved.'}
            </p>
            <div className={s.modalActions}>
              <button type="button" className={s.secondary} onClick={() => setSkipConfirmOpen(false)}>
                {lang === 'ja' ? 'いいえ' : 'No'}
              </button>
              <button type="button" className={s.primary} onClick={confirmSkip} disabled={exportSaving}>
                {lang === 'ja' ? 'はい' : 'Yes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
