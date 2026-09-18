import React from 'react'
import DetailPanel from '../components/DetailPanel/DetailPanel.jsx'
import { emit } from '../logging/operationLog.js'
import s from './FinalDetailPage.module.css'

export default function FinalDetailPage({ sim, onBack }) {
  const {
    history = [],
    sensitivityHistories = {},
    currentValues,
    cycle,
    year,
    llmCommentary,
    llmLoading,
    residentCouncil,
    residentCouncilLoading,
    residentCouncilError,
    residentInterviews = {},
    residentInterviewLoading = {},
    rcpValue,
  } = sim.gameState

  return (
    <div className={s.page}>
      <header className={s.header}>
        <div>
          <span className={s.eyebrow}>2026–2100</span>
          <h1>最終結果の詳細</h1>
          <p>75年間の推移と、最後の25年間に対する住民の反応を確認できます。</p>
        </div>
        <button type="button" onClick={onBack}>最終結果に戻る</button>
      </header>
      <main className={s.detailArea}>
        <DetailPanel
          history={history}
          sensitivityHistories={sensitivityHistories}
          currentValues={currentValues}
          cycle={cycle}
          year={year}
          llmCommentary={llmCommentary}
          llmLoading={llmLoading}
          residentCouncil={residentCouncil}
          residentCouncilLoading={residentCouncilLoading}
          residentCouncilError={residentCouncilError}
          residentInterviews={residentInterviews}
          residentInterviewLoading={residentInterviewLoading}
          onRequestResidentInterview={sim.requestResidentInterview}
          rcpValue={rcpValue}
          onSelectIndicator={(key) => emit('final_detail_indicator_select', { indicator_key: key })}
        />
      </main>
    </div>
  )
}
