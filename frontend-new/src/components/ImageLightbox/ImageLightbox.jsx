import React, { useEffect } from 'react'
import s from './ImageLightbox.module.css'

/** Full-viewport image viewer opened by clicking a diagram. */
export default function ImageLightbox({ src, alt = '', onClose }) {
  useEffect(() => {
    if (!src) return undefined
    function onKey(e) {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [src, onClose])

  if (!src) return null

  return (
    <div
      className={s.overlay}
      role="dialog"
      aria-modal="true"
      aria-label={alt || '拡大表示'}
      onClick={onClose}
    >
      <button type="button" className={s.closeBtn} onClick={onClose} aria-label="閉じる">
        ×
      </button>
      <img
        className={s.image}
        src={src}
        alt={alt}
        onClick={e => e.stopPropagation()}
      />
    </div>
  )
}
