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
import CompletionPage from './pages/CompletionPage.jsx'
import AudioController from './components/AudioController/AudioController.jsx'

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

  let page = null
  if (phase === 'entry') {
    page = <EntryPage key={sim.gameState.entryMountId ?? 0} onStart={sim.startGame} />
  }
  if (phase === 'game')        page = <GamePage sim={sim} />
  if (phase === 'consequence') page = <ConsequencePage sim={sim} onDismiss={sim.dismissConsequence} />
  if (phase === 'completion') page = <CompletionPage onContinue={sim.showFinalResults} />
  if (phase === 'survey') {
    page = (
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
    page = <FinishedPage onReturnToEntry={sim.returnToEntry} />
  }
  if (phase === 'ending') {
    page = (
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
  if (phase === 'final_detail') page = <FinalDetailPage sim={sim} onBack={sim.backFromFinalDetails} />
  if (phase === 'scenario_exploration') page = <ScenarioExplorationPage sim={sim} onBack={sim.backFromScenarioExploration} />
  if (phase === 'comparison')  page = <ResultComparisonPage sim={sim} onBack={sim.backToEnding} />

  return (
    <>
      {page}
      <AudioController phase={phase} event={sim.gameState.pendingEvents?.[0]} />
    </>
  )
}
