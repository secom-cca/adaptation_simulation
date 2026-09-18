import React from 'react'
import { useSimulation } from './hooks/useSimulation.js'
import EntryPage from './pages/EntryPage.jsx'
import GamePage from './pages/GamePage.jsx'
import ConsequencePage from './pages/ConsequencePage.jsx'
import EndingPage from './pages/EndingPage.jsx'
import ResultComparisonPage from './pages/ResultComparisonPage.jsx'
import SurveyPage from './pages/SurveyPage.jsx'

export default function App() {
  const sim = useSimulation()
  const {
    phase,
    history,
    currentClimateHistory,
    year,
    cycle,
    llmCommentary,
    llmLoading,
    surveyAnswers,
  } = sim.gameState

  if (phase === 'entry')       return <EntryPage onStart={sim.startGame} />
  if (phase === 'game')        return <GamePage sim={sim} />
  if (phase === 'consequence') return <ConsequencePage sim={sim} onDismiss={sim.dismissConsequence} />
  if (phase === 'survey') {
    return (
      <SurveyPage
        initialAnswers={surveyAnswers}
        onSubmit={sim.submitSurvey}
        onCancel={sim.cancelSurvey}
      />
    )
  }
  if (phase === 'ending') {
    return (
      <EndingPage
        sim={sim}
        onRestart={sim.restart}
        onCompare={sim.showComparison}
        onOpenSurvey={sim.openSurvey}
        onRetryExport={sim.retryExportLog}
      />
    )
  }
  if (phase === 'comparison')  return <ResultComparisonPage sim={sim} onBack={sim.backToEnding} />
  return null
}
