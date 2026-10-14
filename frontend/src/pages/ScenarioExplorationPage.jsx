import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import s from './ScenarioExplorationPage.module.css'

const API = import.meta.env.VITE_API_BASE || '/api'
const CHART_METRICS = [
  { key: 'flood_damage_jpy', label: '洪水被害（75年累計）', axisLabel: '洪水被害（億円）', scale: value => Number(value || 0) / 100_000_000, digits: 1 },
  { key: 'crop_yield', label: '農作物生産高（75年平均）', axisLabel: '農作物生産高（kg/ha）', scale: value => Number(value || 0), digits: 0 },
  { key: 'ecosystem_level', label: '生態系（75年平均）', axisLabel: '生態系（%）', scale: value => Number(value || 0), digits: 1 },
  { key: 'public_cost_jpy', label: '公的出費（75年累計）', axisLabel: '公的出費（億円）', scale: value => Number(value || 0) / 100_000_000, digits: 1 },
]

function chartMetric(key) {
  return CHART_METRICS.find(metric => metric.key === key) ?? CHART_METRICS[0]
}

function tickFormatter(metric) {
  return value => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: metric.digits })
}

function numericDomain(values) {
  const finite = values.filter(Number.isFinite)
  if (!finite.length) return [0, 1]
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const span = max - min
  const padding = span > 0 ? span * 0.07 : Math.max(Math.abs(max) * 0.07, 1)
  return [Math.max(0, min - padding), max + padding]
}

function mean(rows, key) {
  if (!rows.length) return 0
  return rows.reduce((sum, row) => sum + (Number(row[key]) || 0), 0) / rows.length
}

function playerOutcome(history = []) {
  return {
    flood_damage_jpy: history.reduce((sum, row) => sum + (Number(row['Flood Damage JPY']) || 0), 0),
    crop_yield: mean(history, 'Crop Yield'),
    ecosystem_level: mean(history, 'Ecosystem Level'),
    public_cost_jpy: history.reduce((sum, row) => sum + (Number(row['Municipal Cost']) || 0), 0),
  }
}

function formatOku(value, digits = 1) {
  return `${(Number(value || 0) / 100_000_000).toLocaleString(undefined, { maximumFractionDigits: digits })}億円`
}

function formatMetric(key, value) {
  if (key === 'flood_damage_jpy' || key === 'public_cost_jpy') return formatOku(value)
  if (key === 'crop_yield') return `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} kg/ha`
  return `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`
}

function policyText(policy, labels = {}) {
  const selected = Object.entries(policy.allocations ?? {})
    .filter(([, points]) => Number(points) > 0)
    .map(([key, points]) => `${labels[key] ?? key} ${points}点`)
  return selected.join(' / ') || '投資なし'
}

function OutcomeRange({ title, metricKey, range, player }) {
  return (
    <article className={s.rangeCard}>
      <span>{title}</span>
      <strong>{formatMetric(metricKey, range?.min)}〜{formatMetric(metricKey, range?.max)}</strong>
      <small>あなたの結果：{formatMetric(metricKey, player)}</small>
    </article>
  )
}

function ScenarioPath({ scenario, labels }) {
  if (!scenario) return null
  return (
    <div className={s.pathDetail}>
      <div className={s.pathMetrics}>
        <span>洪水被害<strong>{formatOku(scenario.flood_damage_jpy)}</strong></span>
        <span>農作物生産高<strong>{formatMetric('crop_yield', scenario.crop_yield)}</strong></span>
        <span>生態系<strong>{formatMetric('ecosystem_level', scenario.ecosystem_level)}</strong></span>
        <span>公的出費<strong>{formatOku(scenario.public_cost_jpy)}</strong></span>
      </div>
      <div className={s.turnList}>
        {(scenario.policies ?? []).map(policy => (
          <div className={s.turnRow} key={policy.turn}>
            <strong>第{policy.turn}ターン</strong>
            <div>
              <span>{policy.package_name}・予算{policy.budget}点</span>
              <p>{policyText(policy, labels)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ScatterTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload ?? {}
  return (
    <div className={s.chartTooltip}>
      <strong>{point.player ? 'あなたの結果' : `シナリオ #${point.id}`}</strong>
      <span>洪水被害：{formatOku(point.flood_damage_jpy)}</span>
      <span>農作物：{formatMetric('crop_yield', point.crop_yield)}</span>
      <span>生態系：{formatMetric('ecosystem_level', point.ecosystem_level)}</span>
      <span>公的出費：{formatOku(point.public_cost_jpy)}</span>
      {point.pareto && <b>パレート解</b>}
    </div>
  )
}

function ThreeDOutcomeChart({ points, player, ranges }) {
  const [rotation, setRotation] = useState({ yaw: -0.55, pitch: 0.32 })
  const dragRef = useRef(null)
  const normalize = (key, value) => {
    const range = ranges?.[key]
    const min = Number(range?.min) || 0
    const max = Number(range?.max) || min + 1
    return Math.max(0, Math.min(1, (Number(value) - min) / Math.max(max - min, 1e-9)))
  }
  const projectCoordinates = ([x, y, z]) => {
    const cosYaw = Math.cos(rotation.yaw)
    const sinYaw = Math.sin(rotation.yaw)
    const cosPitch = Math.cos(rotation.pitch)
    const sinPitch = Math.sin(rotation.pitch)
    const yawX = x * cosYaw + z * sinYaw
    const yawZ = -x * sinYaw + z * cosYaw
    const pitchY = y * cosPitch - yawZ * sinPitch
    const depth = y * sinPitch + yawZ * cosPitch
    const perspective = 1 / (1 + depth * 0.38)
    return {
      x: 450 + yawX * 570 * perspective,
      y: 215 - pitchY * 350 * perspective,
      depth,
    }
  }
  const projectPoint = point => projectCoordinates([
    normalize('flood_damage_jpy', point.flood_damage_jpy) - 0.5,
    normalize('crop_yield', point.crop_yield) - 0.5,
    normalize('ecosystem_level', point.ecosystem_level) - 0.5,
  ])
  const cubeCoordinates = {
    o: [-0.5, -0.5, -0.5], x: [0.5, -0.5, -0.5], y: [-0.5, 0.5, -0.5], z: [-0.5, -0.5, 0.5],
    xy: [0.5, 0.5, -0.5], xz: [0.5, -0.5, 0.5], yz: [-0.5, 0.5, 0.5], xyz: [0.5, 0.5, 0.5],
  }
  const cube = Object.fromEntries(Object.entries(cubeCoordinates).map(([key, value]) => [key, projectCoordinates(value)]))
  const edges = [
    ['o', 'x'], ['o', 'y'], ['o', 'z'], ['x', 'xy'], ['x', 'xz'],
    ['y', 'xy'], ['y', 'yz'], ['z', 'xz'], ['z', 'yz'],
    ['xy', 'xyz'], ['xz', 'xyz'], ['yz', 'xyz'],
  ]
  const ordered = points
    .map(point => ({ point, position: projectPoint(point) }))
    .sort((a, b) => b.position.depth - a.position.depth)
  const playerPosition = projectPoint(player)
  const axisLabels = [
    { text: '洪水被害', position: projectCoordinates([0.72, -0.5, -0.5]) },
    { text: '農作物', position: projectCoordinates([-0.5, 0.72, -0.5]) },
    { text: '生態系', position: projectCoordinates([-0.5, -0.5, 0.72]) },
  ]

  const startDrag = event => {
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, ...rotation }
  }
  const moveDrag = event => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    setRotation({
      yaw: drag.yaw + (event.clientX - drag.x) * 0.009,
      pitch: Math.max(-1.2, Math.min(1.2, drag.pitch - (event.clientY - drag.y) * 0.009)),
    })
  }
  const endDrag = event => {
    if (dragRef.current?.pointerId !== event.pointerId) return
    dragRef.current = null
    event.currentTarget.releasePointerCapture?.(event.pointerId)
  }

  return (
    <div>
      <div className={s.threeDControls}>
        <span>図をドラッグして回転できます</span>
        <button type="button" onClick={() => setRotation({ yaw: -0.55, pitch: 0.32 })}>向きを戻す</button>
      </div>
      <div className={s.threeDWrap}>
      <svg
        viewBox="0 0 900 430"
        role="img"
        aria-label="ドラッグして回転できる、洪水被害、農作物生産高、生態系の3次元散布図"
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <g className={s.cubeLines}>
          {edges.map(([from, to]) => (
            <line key={`${from}-${to}`} x1={cube[from].x} y1={cube[from].y} x2={cube[to].x} y2={cube[to].y} />
          ))}
        </g>
        <g className={s.cubeLabels}>
          {axisLabels.map(label => <text key={label.text} x={label.position.x} y={label.position.y}>{label.text}</text>)}
        </g>
        <g>
          {ordered.map(({ point, position }) => (
              <circle
                key={point.id}
                cx={position.x}
                cy={position.y}
                r={point.pareto ? 4 : 2.4}
                className={point.pareto ? s.threeDParetoPoint : s.threeDPoint}
              >
                <title>{`#${point.id}｜洪水 ${formatOku(point.flood_damage_jpy)}｜農作物 ${formatMetric('crop_yield', point.crop_yield)}｜生態系 ${formatMetric('ecosystem_level', point.ecosystem_level)}`}</title>
              </circle>
          ))}
          <polygon
            points={`${playerPosition.x},${playerPosition.y - 8} ${playerPosition.x + 7},${playerPosition.y} ${playerPosition.x},${playerPosition.y + 8} ${playerPosition.x - 7},${playerPosition.y}`}
            className={s.threeDPlayerPoint}
          >
            <title>あなたの結果</title>
          </polygon>
        </g>
      </svg>
      </div>
    </div>
  )
}

export default function ScenarioExplorationPage({ sim, onBack }) {
  const { history = [], mode = 'team', rcpValue = 4.5 } = sim.gameState
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [xMetricKey, setXMetricKey] = useState('flood_damage_jpy')
  const [yMetricKey, setYMetricKey] = useState('crop_yield')
  const player = useMemo(() => playerOutcome(history), [history])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')
    fetch(`${API}/scenario-exploration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        rcp_value: rcpValue === 'composite' ? 4.5 : Number(rcpValue),
      }),
      signal: controller.signal,
    })
      .then(async response => {
        if (!response.ok) throw new Error(await response.text())
        return response.json()
      })
      .then(result => {
        setData(result)
        setSelectedId(String(result.pareto_scenarios?.[0]?.id ?? ''))
      })
      .catch(err => {
        if (err.name !== 'AbortError') setError(err.message || '探索結果を取得できませんでした。')
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [mode, rcpValue])

  const selectedScenario = data?.pareto_scenarios?.find(item => String(item.id) === selectedId)
  const xMetric = chartMetric(xMetricKey)
  const yMetric = chartMetric(yMetricKey)
  const allChartRows = [...(data?.points ?? []), player]
  const scatterPoints = (data?.points ?? []).map(point => ({
    ...point,
    x: xMetric.scale(point[xMetricKey]),
    y: yMetric.scale(point[yMetricKey]),
  }))
  const playerPoint = [{ ...player, x: xMetric.scale(player[xMetricKey]), y: yMetric.scale(player[yMetricKey]), player: true }]
  const xDomain = numericDomain(allChartRows.map(row => xMetric.scale(row[xMetricKey])))
  const yDomain = numericDomain(allChartRows.map(row => yMetric.scale(row[yMetricKey])))

  const changeXMetric = nextKey => {
    if (nextKey === yMetricKey) setYMetricKey(xMetricKey)
    setXMetricKey(nextKey)
  }

  const changeYMetric = nextKey => {
    if (nextKey === xMetricKey) setXMetricKey(yMetricKey)
    setYMetricKey(nextKey)
  }

  return (
    <main className={s.page}>
      <div className={s.content}>
        <div className={s.headerRow}>
          <div>
            <span className={s.kicker}>SCENARIO EXPLORATION</span>
            <h1>あり得た適応シナリオ</h1>
            <p>3ターンの政策経路を総当たりし、2100年までに到達し得た結果の幅を示します。</p>
          </div>
          <button type="button" className={s.backButton} onClick={onBack}>最終結果へ戻る</button>
        </div>

        {loading && <section className={s.stateCard}><div className={s.spinner} /><strong>シナリオを探索しています…</strong><span>初回は数秒かかります。</span></section>}
        {!loading && error && <section className={s.stateCard}><strong>探索結果を読み込めませんでした</strong><span>{error}</span></section>}

        {!loading && data && (
          <>
            <section className={s.methodCard}>
              <strong>{data.package_count}種類の代表政策 × 3ターン：{data.scenario_count.toLocaleString()}経路を全探索</strong>
              <p>各ターンの予算減少や政策上限も反映しています。点単位の全配分はチームモードで理論上約32億経路になるため、この画面では意味の異なる代表政策パッケージの全順列を比較しています。</p>
              <span>RCP{data.rcp_value}・パレート解 {data.pareto_count}件</span>
            </section>

            <section className={s.rangeGrid}>
              <OutcomeRange title="洪水被害（75年累計）" metricKey="flood_damage_jpy" range={data.ranges.flood_damage_jpy} player={player.flood_damage_jpy} />
              <OutcomeRange title="農作物生産高（75年平均）" metricKey="crop_yield" range={data.ranges.crop_yield} player={player.crop_yield} />
              <OutcomeRange title="生態系（75年平均）" metricKey="ecosystem_level" range={data.ranges.ecosystem_level} player={player.ecosystem_level} />
              <OutcomeRange title="公的出費（75年累計）" metricKey="public_cost_jpy" range={data.ranges.public_cost_jpy} player={player.public_cost_jpy} />
            </section>

            <section className={s.chartCard}>
              <div className={s.sectionHeading}>
                <div><span>全探索の分布</span><h2>{xMetric.label}と{yMetric.label}のトレードオフ</h2></div>
                <div className={s.legend}><span><i className={s.normalDot} />探索経路</span><span><i className={s.paretoDot} />パレート解</span><span><i className={s.playerDot} />あなた</span></div>
              </div>
              <div className={s.axisControls}>
                <label>横軸<select value={xMetricKey} onChange={event => changeXMetric(event.target.value)}>{CHART_METRICS.map(metric => <option key={metric.key} value={metric.key}>{metric.label}</option>)}</select></label>
                <button type="button" onClick={() => { setXMetricKey(yMetricKey); setYMetricKey(xMetricKey) }} aria-label="横軸と縦軸を入れ替える">⇄</button>
                <label>縦軸<select value={yMetricKey} onChange={event => changeYMetric(event.target.value)}>{CHART_METRICS.map(metric => <option key={metric.key} value={metric.key}>{metric.label}</option>)}</select></label>
              </div>
              <div className={s.chartWrap}>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 12, right: 24, bottom: 48, left: 42 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(60,80,95,.14)" />
                    <XAxis type="number" dataKey="x" name={xMetric.label} domain={xDomain} tickFormatter={tickFormatter(xMetric)} tick={{ fontSize: 11 }} label={{ value: xMetric.axisLabel, position: 'insideBottom', offset: -30 }} />
                    <YAxis type="number" dataKey="y" name={yMetric.label} domain={yDomain} tickFormatter={tickFormatter(yMetric)} width={82} tick={{ fontSize: 11 }} label={{ value: yMetric.axisLabel, angle: -90, position: 'insideLeft', offset: -28 }} />
                    <Tooltip content={<ScatterTooltip />} />
                    <Scatter data={scatterPoints}>
                      {scatterPoints.map(point => <Cell key={point.id} fill={point.pareto ? '#4a8c5c' : 'rgba(61,107,143,.35)'} />)}
                    </Scatter>
                    <Scatter data={playerPoint} fill="#bf4545" shape="star" />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
              <p className={s.chartNote}>軸の単位はタイトルにまとめ、探索結果とあなたの結果を含む範囲から目盛りを計算しています。</p>
            </section>

            <section className={s.chartCard}>
              <div className={s.sectionHeading}>
                <div><span>3D OUTCOMES</span><h2>洪水被害 × 農作物生産高 × 生態系</h2></div>
                <div className={s.legend}><span><i className={s.normalDot} />探索経路</span><span><i className={s.paretoDot} />パレート解</span><span><i className={s.playerDot} />あなた</span></div>
              </div>
              <ThreeDOutcomeChart points={data.points} player={player} ranges={data.ranges} />
              <p className={s.chartNote}>公的出費を除く3指標を、正規化した3D空間から投影しています。右ほど洪水被害が大きく、上ほど農作物生産高、右上方向の奥行きほど生態系が高い結果です。</p>
            </section>

            <section className={s.representativeSection}>
              <div className={s.sectionHeading}><div><span>代表解</span><h2>目的によって異なる政策経路</h2></div></div>
              <div className={s.representativeGrid}>
                {data.representatives.map(scenario => (
                  <article className={s.representativeCard} key={scenario.kind}>
                    <h3>{scenario.label}</h3>
                    <ScenarioPath scenario={scenario} labels={data.policy_labels} />
                  </article>
                ))}
              </div>
            </section>

            <section className={s.paretoSection}>
              <div className={s.sectionHeading}>
                <div><span>PARETO FRONT</span><h2>パレート解を詳しく見る</h2></div>
                <select value={selectedId} onChange={event => setSelectedId(event.target.value)}>
                  {data.pareto_scenarios.map(scenario => (
                    <option key={scenario.id} value={scenario.id}>解 #{scenario.id}・バランス {scenario.balanced_score.toFixed(1)}</option>
                  ))}
                </select>
              </div>
              <ScenarioPath scenario={selectedScenario} labels={data.policy_labels} />
            </section>
          </>
        )}
      </div>
    </main>
  )
}
