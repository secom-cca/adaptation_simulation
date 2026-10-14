import React from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import s from './FinishedPage.module.css'

export default function FinishedPage({ onReturnToEntry }) {
  const { lang } = useTranslation()

  return (
    <div className={s.page}>
      <div className={s.card} role="status">
        <p className={s.eyebrow}>{lang === 'ja' ? 'SESSION COMPLETE' : 'SESSION COMPLETE'}</p>
        <h1 className={s.title}>
          {lang === 'ja'
            ? 'これにてゲームプレイは終了です。'
            : 'This concludes the gameplay session.'}
        </h1>
        <p className={s.lede}>
          {lang === 'ja'
            ? 'プレイしてくれてありがとうございました！'
            : 'Thank you for playing!'}
        </p>
        <button type="button" className={s.primary} onClick={onReturnToEntry}>
          {lang === 'ja' ? '初期画面に戻る' : 'Return to start'}
        </button>
      </div>
    </div>
  )
}
