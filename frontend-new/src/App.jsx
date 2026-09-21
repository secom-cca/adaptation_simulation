import React from 'react'
import { useSimulation } from './hooks/useSimulation.js'
import EntryPage from './pages/EntryPage.jsx'
import GamePage from './pages/GamePage.jsx'
import ConsequencePage from './pages/ConsequencePage.jsx'
import EndingPage from './pages/EndingPage.jsx'
import ResultComparisonPage from './pages/ResultComparisonPage.jsx'
import SurveyPage from './pages/SurveyPage.jsx'
import FinishedPage from './pages/FinishedPage.jsx'
import FinalDetailPage from './pages/FinalDetailPage.jsx'
import ScenarioExplorationPage from './pages/ScenarioExplorationPage.jsx'

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

  if (phase === 'entry') {
    return <EntryPage key={sim.gameState.entryMountId ?? 0} onStart={sim.startGame} />
  }
  if (phase === 'game')        return <GamePage sim={sim} />
  if (phase === 'consequence') return <ConsequencePage sim={sim} onDismiss={sim.dismissConsequence} />
  if (phase === 'survey') {
    return (
      <SurveyPage
        initialAnswers={surveyAnswers}
        exportSaving={sim.gameState.exportSaving}
        onCancel={sim.cancelSurvey}
        onSubmitAndRestart={sim.submitSurveyAndRestart}
        onSkipAndRestart={sim.skipSurveyAndRestart}
      />
    )
  }
  if (phase === 'finished') {
    return <FinishedPage onReturnToEntry={sim.returnToEntry} />
  }
  if (phase === 'ending') {
    return (
      <EndingPage
        sim={sim}
        onCompare={sim.showComparison}
        onExplore={sim.openScenarioExploration}
        onOpenDetails={sim.openFinalDetails}
        onOpenSurvey={sim.openSurvey}
        onRetryExport={sim.retryExportLog}
      />
    )
  }
  if (phase === 'final_detail') return <FinalDetailPage sim={sim} onBack={sim.backFromFinalDetails} />
  if (phase === 'scenario_exploration') return <ScenarioExplorationPage sim={sim} onBack={sim.backFromScenarioExploration} />
  if (phase === 'comparison')  return <ResultComparisonPage sim={sim} onBack={sim.backToEnding} />
  return null
}
