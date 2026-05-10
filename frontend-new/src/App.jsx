import React from 'react'
import { useSimulation } from './hooks/useSimulation.js'
import EntryPage from './pages/EntryPage.jsx'
import GamePage from './pages/GamePage.jsx'
import ConsequencePage from './pages/ConsequencePage.jsx'
import CycleReport from './components/CycleReport/CycleReport.jsx'
import EndingPage from './pages/EndingPage.jsx'
import ResultComparisonPage from './pages/ResultComparisonPage.jsx'

export default function App() {
  const sim = useSimulation()
  const { phase, history, year, cycle } = sim.gameState

  if (phase === 'entry')       return <EntryPage onStart={sim.startGame} />
  if (phase === 'game')        return <GamePage sim={sim} />
  if (phase === 'report')      return <CycleReport history={history} year={year} cycle={cycle} onViewDetails={sim.dismissReport} />
  if (phase === 'consequence') return <ConsequencePage sim={sim} onDismiss={sim.dismissConsequence} />
  if (phase === 'ending')      return <EndingPage sim={sim} onRestart={sim.restart} onCompare={sim.showComparison} />
  if (phase === 'comparison')  return <ResultComparisonPage sim={sim} onBack={sim.backToEnding} />
  return null
}
