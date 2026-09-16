import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import TopBar from '../components/TopBar/TopBar.jsx'
import DetailPanel from '../components/DetailPanel/DetailPanel.jsx'
import DecisionPanel from '../components/DecisionPanel/DecisionPanel.jsx'
import { buildBudgetRows, findAllowedPolicyPoints } from '../data/budget.js'
import { emit, setLogContext } from '../logging/operationLog.js'
import s from './GamePage.module.css'

const POLICY_PREVIEW_IMAGES = {
  planting_trees_amount: {
    file: 'forest.png',
    label: { en: 'Forest Planting', ja: '植林・森林保全' },
  },
  dam_levee_construction_cost: {
    file: 'levee.png',
    label: { en: 'Levee Investment', ja: '堤防・洪水対策' },
  },
  paddy_dam_construction_cost: {
    file: 'paddy-dam.png',
    label: { en: 'Paddy Field Dam', ja: '田んぼダム' },
  },
  house_migration_amount: {
    file: 'relocation.png',
    label: { en: 'Relocation Support', ja: '移住・適応支援' },
  },
  capacity_building_cost: {
    file: 'preparedness.png',
    label: { en: 'Disaster Preparedness', ja: '防災能力構築' },
  },
  agricultural_RnD_cost: {
    file: 'agri-rnd.png',
    label: { en: 'Agricultural R&D', ja: '農業技術研究' },
  },
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
  const { gameState, advanceCycle, setGameView, requestResidentInterview } = sim
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
    rcpValue,
  } = gameState

  const view = gameView ?? 'simple'
  const [hasNewResults, setHasNewResults] = useState(false)
  const [policyPreview, setPolicyPreview] = useState(null)
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

  const { t, lang } = useTranslation()
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

  const handlePreviewPolicy = useCallback((key, rect) => {
    if (!key) {
      if (policyPreview?.key) {
        emit('policy_preview_close', { policy_key: policyPreview.key })
      }
      setPolicyPreview(null)
      return
    }

    if (POLICY_PREVIEW_IMAGES[key] && rect) {
      emit('policy_preview_open', { policy_key: key })
      setPolicyPreview({
        key,
        left: rect.left + rect.width / 2,
        top: rect.top - 12,
        width: Math.min(460, Math.max(320, rect.width * 1.95)),
      })
    }
  }, [policyPreview?.key])

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
            </div>
            <div className={s.rightStack}>
              <section className={s.systemCard}>
                <img src="/system_dynamics_ja2.png" alt="システムダイナミクス図" />
              </section>
              <section className={s.policyTableCard}>
                <img src="/policy-effects-table.png" alt="政策効果の比較表" />
              </section>
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
            onSelectIndicator={(key) => {
              emit('detail_indicator_select', { indicator_key: key }, {
                context: { phase: 'game', cycle, year, gameView: 'detail' },
              })
            }}
          />
        )}
        {policyPreview && POLICY_PREVIEW_IMAGES[policyPreview.key] && (
          <div
            className={s.policyPreview}
            style={{
              left: `${policyPreview.left}px`,
              top: `${policyPreview.top}px`,
              width: `${policyPreview.width}px`,
            }}
            aria-live="polite"
          >
            <img
              className={s.policyPreviewImage}
              src={`/causal-explorer-assets/policy-mini-maps/${lang === 'ja' ? 'ja' : 'en'}/${POLICY_PREVIEW_IMAGES[policyPreview.key].file}`}
              alt={POLICY_PREVIEW_IMAGES[policyPreview.key].label[lang === 'ja' ? 'ja' : 'en']}
            />
          </div>
        )}
      </div>

      {/* ── Fixed decision panel ── */}
      <DecisionPanel
        mode={mode}
        sliders={sliders}
        onSliderChange={handleSliderChange}
        onPreviewPolicy={handlePreviewPolicy}
        onAdvance={handleAdvance}
        loading={loading}
        year={year}
        policyHistory={policyHistory}
        budgetRow={currentBudgetRow}
      />

      {error && <div className={s.errorBanner}>{error}</div>}
    </div>
  )
}
