import React, { useState, useEffect, useRef, useCallback } from 'react'
import TopBar from '../components/TopBar/TopBar.jsx'
import DetailPanel from '../components/DetailPanel/DetailPanel.jsx'
import DecisionPanel from '../components/DecisionPanel/DecisionPanel.jsx'
import ImageLightbox from '../components/ImageLightbox/ImageLightbox.jsx'
import { buildBudgetRows, findAllowedPolicyPoints } from '../data/budget.js'
import { emit, setLogContext } from '../logging/operationLog.js'
import IntentSurveyModal from '../components/IntentSurvey/IntentSurveyModal.jsx'
import s from './GamePage.module.css'

const POLICY_HIGHLIGHTS = {
  planting_trees_amount:       { x: 23, y: 18, rx: 18, ry: 17 },
  dam_levee_construction_cost: { x: 70, y: 34, rx: 13, ry: 15 },
  paddy_dam_construction_cost: { x: 61, y: 12, rx: 12, ry: 11 },
  house_migration_amount:      { x: 39, y: 80, rx: 17, ry: 16 },
  capacity_building_cost:      { x: 89, y: 53, rx: 10, ry: 13 },
  agricultural_RnD_cost:       { x: 88, y: 21, rx: 11, ry: 13 },
}

// Positions refer to the visible areas of the 4:3 basin movie when it is
// center-cropped into the left column.
const SCENE_HIGHLIGHTS = {
  planting_trees_amount:       { x: 84, y: 12, rx: 17, ry: 18 },
  dam_levee_construction_cost: { x: 51, y: 43, rx: 29, ry: 16 },
  paddy_dam_construction_cost: { x: 76, y: 83, rx: 20, ry: 15 },
  house_migration_amount:      { x: 84, y: 30, rx: 18, ry: 20 },
  capacity_building_cost:      { x: 36, y: 21, rx: 25, ry: 18 },
  agricultural_RnD_cost:       { x: 76, y: 83, rx: 22, ry: 17 },
}

const BACKGROUND_VIDEO_BY_TIER = {
  T1D1: '/bg.mp4',
  T1D2: '/videos/T1D2.mp4',
  T1D3: '/videos/T1D3.mp4',
  T2D1: '/videos/T2D1.mp4',
  T2D2: '/bg.mp4',
  T2D3: '/videos/T2D3.mp4',
  T3D1: '/videos/T3D1.mp4',
  T3D2: '/videos/T3D2.mp4',
  T3D3: '/videos/T3D3.mp4',
}

function cumulativeSliderPoints(policyHistory = [], key) {
  return policyHistory.reduce((sum, entry) => sum + (Number(entry?.sliders?.[key]) || 0), 0)
}

function tierFromPoints(points) {
  if (points >= 10) return 3
  if (points >= 5) return 2
  return 1
}

function backgroundVideoForState(policyHistory = [], sliders = {}) {
  const treePoints = cumulativeSliderPoints(policyHistory, 'planting_trees_amount')
    + (Number(sliders.planting_trees_amount) || 0)
  const defensePoints = cumulativeSliderPoints(policyHistory, 'dam_levee_construction_cost')
    + cumulativeSliderPoints(policyHistory, 'paddy_dam_construction_cost')
    + (Number(sliders.dam_levee_construction_cost) || 0)
    + (Number(sliders.paddy_dam_construction_cost) || 0)
  const key = `T${tierFromPoints(treePoints)}D${tierFromPoints(defensePoints)}`
  return BACKGROUND_VIDEO_BY_TIER[key] ?? BACKGROUND_VIDEO_BY_TIER.T1D1
}

export default function GamePage({ sim }) {
  const {
    gameState,
    advanceCycle,
    submitIntentSurvey,
    cancelIntentSurvey,
    setGameView,
    dismissIntroduction,
    requestResidentInterview,
  } = sim
  const {
    year,
    cycle,
    mode,
    history,
    sensitivityHistories = {},
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
    intentSurveyOpen = false,
    intentSurveySubmitted = false,
    intentSurveyCycle,
    intentSurveyYear,
    advanceResultReady = false,
    rcpValue,
    introDismissed = false,
  } = gameState

  const view = gameView ?? 'simple'
  const [hasNewResults, setHasNewResults] = useState(false)
  const [activePolicyKey, setActivePolicyKey] = useState(null)
  const [showPolicyComparison, setShowPolicyComparison] = useState(false)
  const [lightbox, setLightbox] = useState(null)
  const prevLoadingRef = useRef(false)
  const closeLightbox = useCallback(() => setLightbox(null), [])

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

  const isTeam = mode === 'team'
  const budgetRows = buildBudgetRows(policyHistory, history, { year, sliders })
  const currentBudgetRow = budgetRows[budgetRows.length - 1] ?? null
  const backgroundVideo = backgroundVideoForState(policyHistory, sliders)

  useEffect(() => {
    setLogContext({
      phase: 'game',
      cycle,
      year,
      gameView: view,
    })
  }, [cycle, year, view])

  const handleSliderChange = useCallback((key, value, source = 'ui') => {
    setSliders(prev => {
      const requested = Number(value) || 0
      const allowedValue = findAllowedPolicyPoints(policyHistory, history, year, prev, key, requested)
      const from = Number(prev[key]) || 0
      if (from !== allowedValue) {
        const next = { ...prev, [key]: allowedValue }
        const nextBudgetRows = buildBudgetRows(policyHistory, history, { year, sliders: next })
        const nextBudget = nextBudgetRows[nextBudgetRows.length - 1]
        emit('policy_slider_change', {
          policy_key: key,
          from,
          to: allowedValue,
          requested,
          clamped: requested !== allowedValue,
          available_budget_points: nextBudget?.availableBudgetPoints ?? null,
          used_policy_points_after: nextBudget?.usedPolicyPoints ?? null,
        }, {
          source,
          context: { phase: 'game', cycle, year, gameView: view },
        })
      }
      return { ...prev, [key]: allowedValue }
    })
  }, [cycle, history, policyHistory, view, year])

  const handlePolicySelect = useCallback((key) => {
    setActivePolicyKey(key)
    emit('policy_tab_select', { policy_key: key })
  }, [])

  const handlePolicyComparisonToggle = useCallback(() => {
    setShowPolicyComparison(current => {
      emit('policy_comparison_toggle', { open: !current })
      return !current
    })
  }, [])

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
              handleSliderChange(key, numValue, 'camera_ws')
              emit('camera_slider_update', {
                policy_key: key,
                value: numValue,
              }, {
                source: 'camera_ws',
                context: { phase: 'game', cycle, year, gameView: view },
              })
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
  }, [cycle, handleSliderChange, view, year])

  return (
    <div className={`${s.page} ${isTeam ? 'teamMode' : ''}`}>
      <TopBar
        year={year}
        cycle={cycle}
        mode={mode}
        view={view}
        onSetView={handleSetView}
        hasNewResults={hasNewResults}
      />

      {/* ── Main area ── */}
      <div className={`${s.mainArea} ${view !== 'simple' ? s.detailMode : ''}`}>
        {view === 'simple' && (
          <div className={s.overviewGrid}>
            <div className={s.sceneCard}>
              <video
                key={backgroundVideo}
                className={s.bgCanvas}
                src={backgroundVideo}
                autoPlay
                loop
                muted
                playsInline
                onError={event => {
                  event.currentTarget.onerror = null
                  event.currentTarget.src = '/bg.mp4'
                }}
              />
              {activePolicyKey && SCENE_HIGHLIGHTS[activePolicyKey] && (
                <div
                  className={s.sceneHighlightLayer}
                  style={highlightStyle(SCENE_HIGHLIGHTS[activePolicyKey])}
                  aria-hidden="true"
                >
                  <span className={s.sceneShade} />
                  <span className={s.sceneHighlightRing} />
                </div>
              )}
            </div>
            <div className={s.rightStack}>
              <section className={s.systemCard}>
                <button
                  type="button"
                  className={`${s.policyComparisonButton} ${showPolicyComparison ? s.policyComparisonButtonActive : ''}`}
                  aria-expanded={showPolicyComparison}
                  aria-controls="policy-comparison-table"
                  onClick={handlePolicyComparisonToggle}
                >
                  政策比較
                </button>
                <button
                  type="button"
                  className={`${s.systemFigure} ${s.expandableImage} ${activePolicyKey ? s.hasHighlight : ''}`}
                  style={highlightStyle(POLICY_HIGHLIGHTS[activePolicyKey])}
                  aria-label="システムダイナミクス図を拡大表示"
                  onClick={() => setLightbox({
                    src: '/system_dynamics_ja2.png',
                    alt: 'システムダイナミクス図',
                  })}
                >
                  <img className={s.systemDiagram} src="/system_dynamics_ja2.png" alt="システムダイナミクス図" />
                  {activePolicyKey && (
                    <>
                      <img className={s.highlightDiagram} src="/system_dynamics_ja2.png" alt="" aria-hidden="true" />
                      <span className={s.highlightRing} aria-hidden="true" />
                    </>
                  )}
                </button>
              </section>
              {showPolicyComparison && (
                <section id="policy-comparison-table" className={s.policyTableCard} aria-label="政策比較">
                  <button
                    type="button"
                    className={s.expandableImage}
                    aria-label="政策効果の比較表を拡大表示"
                    onClick={() => setLightbox({
                      src: '/policy-effects-table.png',
                      alt: '政策効果の比較表',
                    })}
                  >
                    <img src="/policy-effects-table.png" alt="政策効果の比較表" />
                  </button>
                </section>
              )}
            </div>
          </div>
        )}
        {view === 'detail' && (
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
            onRequestResidentInterview={requestResidentInterview}
            rcpValue={rcpValue}
            rightInset
            onSelectIndicator={(key) => {
              emit('detail_indicator_select', { indicator_key: key }, {
                context: { phase: 'game', cycle, year, gameView: 'detail' },
              })
            }}
          />
        )}
        {!introDismissed && view === 'simple' && (
          <IntroductionOverlay onDismiss={dismissIntroduction} />
        )}
      </div>

      {/* ── Fixed decision panel ── */}
      {introDismissed && (
        <DecisionPanel
          mode={mode}
          sliders={sliders}
          onSliderChange={handleSliderChange}
          onPolicySelect={handlePolicySelect}
          onAdvance={handleAdvance}
          loading={loading}
          year={year}
          policyHistory={policyHistory}
          budgetRow={currentBudgetRow}
        />
      )}

      {error && <div className={s.errorBanner}>{error}</div>}

      {intentSurveyOpen && (
        <IntentSurveyModal
          key={`${intentSurveyCycle ?? cycle}-${intentSurveyYear ?? year}`}
          cycle={intentSurveyCycle ?? cycle}
          year={intentSurveyYear ?? year}
          submitted={intentSurveySubmitted}
          simulationReady={advanceResultReady}
          onSubmit={submitIntentSurvey}
          onBack={cancelIntentSurvey}
        />
      )}

      <ImageLightbox
        src={lightbox?.src}
        alt={lightbox?.alt}
        onClose={closeLightbox}
      />
    </div>
  )
}

function IntroductionOverlay({ onDismiss }) {
  return (
    <div className={s.introOverlay} role="dialog" aria-modal="true" aria-labelledby="introduction-title">
      <div className={s.introPanel}>
        <button type="button" className={s.introSkip} onClick={onDismiss}>スキップ</button>
        <div className={`${s.introEyebrow} ${s.introReveal}`} style={{ '--intro-delay': '0ms' }}>
          INTRODUCTION
        </div>
        <h1 id="introduction-title" className={s.introReveal} style={{ '--intro-delay': '450ms' }}>
          あなたは、大きな河川を抱える地方自治体の<strong>政策決定者</strong>です。
        </h1>
        <p className={`${s.introLead} ${s.introReveal}`} style={{ '--intro-delay': '1050ms' }}>
          2100年までを見据え、変わりゆく気候に地域を適応させる政策を決めてください。
        </p>
        <p className={`${s.introTurn} ${s.introReveal}`} style={{ '--intro-delay': '1650ms' }}>
          政策方針を見直せるのは25年ごと。全3ターンです。
        </p>

        <div className={s.introPriorities}>
          <div className={s.introReveal} style={{ '--intro-delay': '2250ms' }}>
            <span>01</span>
            <p><strong>洪水から守る</strong>降水パターンが変化し、極端な大雨が増えていきます。洪水被害を抑えてください。</p>
          </div>
          <div className={s.introReveal} style={{ '--intro-delay': '2950ms' }}>
            <span>02</span>
            <p><strong>暮らしと農業を支える</strong>農業生産を守り、地域住民が暮らし続けられる環境を維持してください。</p>
          </div>
          <div className={s.introReveal} style={{ '--intro-delay': '3650ms' }}>
            <span>03</span>
            <p><strong>環境と負担を考える</strong>生態系へのダメージと、公的出費による住民負担をできるだけ抑えてください。</p>
          </div>
        </div>

        <p className={`${s.introFuture} ${s.introReveal}`} style={{ '--intro-delay': '4350ms' }}>
          目の前の25年だけでなく、その先を生きる将来世代まで考えることがポイントです。
        </p>
        <p className={`${s.introClosing} ${s.introReveal}`} style={{ '--intro-delay': '5000ms' }}>
          施策の組み合わせを探ってみましょう。
        </p>
        <button
          type="button"
          className={`${s.introStart} ${s.introReveal}`}
          style={{ '--intro-delay': '5500ms' }}
          onClick={onDismiss}
        >
          ゲームを始める
        </button>
      </div>
    </div>
  )
}

function highlightStyle(highlight) {
  if (!highlight) return undefined
  return {
    '--spot-x': `${highlight.x}%`,
    '--spot-y': `${highlight.y}%`,
    '--spot-rx': `${highlight.rx}%`,
    '--spot-ry': `${highlight.ry}%`,
  }
}
