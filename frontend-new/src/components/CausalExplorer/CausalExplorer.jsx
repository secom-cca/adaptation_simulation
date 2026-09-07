import React from 'react'
import './CausalExplorer.css'

const ITEMS = [
  ['植林・森林保全', '雨水を一時的にためる力と、生きもののすみかを支えます。'],
  ['堤防・河川改修', '時間遅れで防御水準が上がり、洪水時の越流水を減らします。'],
  ['田んぼダム', '水田に雨水をため、導入面積に応じて流出を抑えます。'],
  ['住宅移転', '洪水リスクの高い地域に残る住宅を減らします。'],
  ['防災訓練', '洪水時の行動理解を広げ、被害を軽減しやすくします。'],
  ['農業R&D', '高温による品質低下や収量低下を抑えやすくします。'],
]

export default function CausalExplorer() {
  // MayFest 2026: simplified fallback keeps the analysis page usable without old burden wording.
  return (
    <div className="causal-explorer causal-explorer--embedded">
      <div className="causal-explorer__panel">
        <h3>政策と主要指標の関係</h3>
        <p>この画面では、洪水被害額・農作物生産性・生態系ポイントに関わる主な政策効果を確認できます。</p>
        <ul>
          {ITEMS.map(([title, body]) => (
            <li key={title}><strong>{title}</strong>: {body}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
