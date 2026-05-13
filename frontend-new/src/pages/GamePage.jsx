import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import TopBar from '../components/TopBar/TopBar.jsx'
import BasinStatus from '../components/BasinStatus/BasinStatus.jsx'
import ScenarioBriefing from '../components/ScenarioBriefing/ScenarioBriefing.jsx'
import DetailPanel from '../components/DetailPanel/DetailPanel.jsx'
import AnalysisPage from './AnalysisPage.jsx'
import DecisionPanel from '../components/DecisionPanel/DecisionPanel.jsx'
import { buildBudgetRows, findAllowedPolicyPoints } from '../data/budget.js'
import s from './GamePage.module.css'

export default function GamePage({ sim }) {
  const { gameState, advanceCycle, setGameView, requestResidentInterview } = sim
  const {
    year,
    cycle,
    mode,
    history,
    currentValues,
    loading,
    error,
    gameView,
    policyHistory = [],
    llmCommentary,
    llmLoading,
    residentCouncil,
    residentCouncilLoading,
    residentCouncilError,
    residentInterviews = {},
    residentInterviewLoading = {},
  } = gameState

  const view = gameView ?? 'simple'
  const [hasNewResults, setHasNewResults] = useState(false)
  const prevLoadingRef = useRef(false)

  useEffect(() => {
    if (prevLoadingRef.current && !loading) {
      setHasNewResults(true)
    }
    prevLoadingRef.current = loading
  }, [loading])

  const handleSetView = useCallback((next) => {
    setGameView(next)
    if (next !== 'simple') setHasNewResults(false)
  }, [setGameView])

  const [sliders, setSliders] = useState({
    planting_trees_amount:       0,
    dam_levee_construction_cost: 0,
    paddy_dam_construction_cost: 0,
    house_migration_amount:      0,
    capacity_building_cost:      0,
    agricultural_RnD_cost:       0,
    transportation_invest:       0,
  })

  const { t } = useTranslation()
  const isTeam = mode === 'team'
  const goalText = t(`goal.${mode}.${Math.min(cycle, 3)}`)
  const budgetRows = buildBudgetRows(policyHistory, history, { year, sliders })
  const currentBudgetRow = budgetRows[budgetRows.length - 1] ?? null

  const handleSliderChange = useCallback((key, value) => {
    setSliders(prev => {
      const allowedValue = findAllowedPolicyPoints(policyHistory, history, year, prev, key, value)
      return { ...prev, [key]: allowedValue }
    })
  }, [history, policyHistory, year])

  const handleAdvance = useCallback(() => {
    const budgetRowsForSelection = buildBudgetRows(policyHistory, history, { year, sliders })
    const budgetRow = budgetRowsForSelection[budgetRowsForSelection.length - 1]
    const safeSliders = { ...sliders }

    if (budgetRow && budgetRow.usedPolicyPoints > budgetRow.availableBudgetPoints) {
      for (const key of Object.keys(safeSliders)) {
        safeSliders[key] = findAllowedPolicyPoints(policyHistory, history, year, safeSliders, key, safeSliders[key])
      }
    }

    advanceCycle(safeSliders)
  }, [advanceCycle, history, policyHistory, sliders, year])

  // WebSocket 受信設定（カメラからのスライダー値反映）
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:3001')

    ws.onopen = () => {
      console.log('✅ WebSocket connected (frontend-new)')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('📨 受信 (ws):', data)

        // スライダーキー（6本の政策）
        const POLICY_KEYS = [
          'planting_trees_amount',
          'dam_levee_construction_cost',
          'agricultural_RnD_cost',
          'house_migration_amount',
          'paddy_dam_construction_cost',
          'capacity_building_cost'
        ]

        // simulate_trigger の場合はスキップ（game は handleAdvance で進める）
        if (data.simulate_trigger === true) {
          console.log('🎬 simulate_trigger 受信')
          return
        }

        // 各キーを処理
        for (const [key, value] of Object.entries(data)) {
          if (key === 'simulate_trigger' || key === 'simulate') continue
          if (POLICY_KEYS.includes(key)) {
            // カメラから送られた値（ポイント形式）をそのまま設定
            const numValue = Number(value)
            if (Number.isFinite(numValue)) {
              handleSliderChange(key, numValue)
            }
          }
        }
      } catch (e) {
        console.warn('⚠️ WebSocket メッセージ解析エラー:', e)
      }
    }

    ws.onerror = (err) => {
      console.error('❌ WebSocket error', err)
    }

    ws.onclose = () => {
      console.warn('⚠️ WebSocket closed')
    }

    return () => ws.close()
  }, [handleSliderChange])

  return (
    <div className={`${s.page} ${isTeam ? 'teamMode' : ''}`}>
      <TopBar
        year={year}
        cycle={cycle}
        mode={mode}
        goal={goalText}
        view={view}
        onSetView={handleSetView}
        hasNewResults={hasNewResults}
      />

      {/* ── Main area ── */}
      <div className={`${s.mainArea} ${view !== 'simple' ? s.detailMode : ''}`}>
        {view === 'simple' && (
          <>
            <video className={s.bgCanvas} src="/bg.mp4" autoPlay loop muted playsInline />
            <BasinStatus currentValues={currentValues} history={history} budgetRow={currentBudgetRow} />
            <div className={s.rightArea}>
              <ScenarioBriefing year={year} cycle={cycle} />
            </div>
          </>
        )}
        {view === 'detail' && (
          <DetailPanel
            history={history}
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
            onRequestResidentInterview={requestResidentInterview}
          />
        )}
        {view === 'analysis' && (
          <AnalysisPage history={history} />
        )}
      </div>

      {/* ── Fixed decision panel ── */}
      <DecisionPanel
        mode={mode}
        sliders={sliders}
        onSliderChange={handleSliderChange}
        onAdvance={handleAdvance}
        loading={loading}
        year={year}
      />

      {error && <div className={s.errorBanner}>{error}</div>}
    </div>
  )
}
