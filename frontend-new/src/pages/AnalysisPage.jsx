import React, { useState } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Label,
} from 'recharts'
import { useTranslation } from '../contexts/LanguageContext.jsx'
import { CHART_KEYS, fmtY } from '../data/indicators.js'
import s from './AnalysisPage.module.css'

const CYCLE_COLORS = ['#3d6b8f', '#4a8c5c', '#c07a3a']

function getCycle(year) {
  if (year <= 2050) return 0
  if (year <= 2075) return 1
  return 2
}

const CustomDot = (props) => {
  const { cx, cy, payload } = props
  const color = CYCLE_COLORS[getCycle(payload.year)] ?? '#888'
  return <circle cx={cx} cy={cy} r={4} fill={color} fillOpacity={0.75} stroke="none" />
}

export default function AnalysisPage({ history }) {
  const { t, lang } = useTranslation()
  const [xKey, setXKey] = useState('Flood Damage JPY')
  const [yKey, setYKey] = useState('Crop Yield')

  const xInd = CHART_KEYS.find(i => i.key === xKey)
  const yInd = CHART_KEYS.find(i => i.key === yKey)

  const scatterData = history
    .filter(row => row[xKey] != null && row[yKey] != null)
    .map(row => ({ x: row[xKey], y: row[yKey], year: row.year }))

  return (
    <div className={s.page}>

      {/* ── Left: CLD diagram ── */}
      <div className={s.cldPanel}>
        <div className={s.panelHeader}>
          <span className={s.panelTitle}>{t('analysis.cld.title')}</span>
          <span className={s.panelSub}>{t('analysis.cld.sub')}</span>
        </div>
        <div className={s.cldWrap}>
          <img src="/system_dynamics_ja2.png" alt="System Dynamics" className={s.cldImg} />
        </div>
      </div>

      {/* ── Right: Scatter plot ── */}
      <div className={s.scatterPanel}>
        <div className={s.panelHeader}>
          <span className={s.panelTitle}>{t('analysis.scatter.title')}</span>
          <span className={s.panelSub}>{t('analysis.scatter.sub')}</span>
        </div>

        {/* axis selectors */}
        <div className={s.selectors}>
          <div className={s.selectorGroup}>
            <span className={s.selectorLabel}>{t('analysis.scatter.y')}</span>
            <select className={s.select} value={yKey} onChange={e => setYKey(e.target.value)}>
              {CHART_KEYS.map(i => (
                <option key={i.key} value={i.key}>
                  {lang === 'ja' ? i.labelJa : i.labelEn}
                </option>
              ))}
            </select>
          </div>
          <div className={s.selectorGroup}>
            <span className={s.selectorLabel}>{t('analysis.scatter.x')}</span>
            <select className={s.select} value={xKey} onChange={e => setXKey(e.target.value)}>
              {CHART_KEYS.map(i => (
                <option key={i.key} value={i.key}>
                  {lang === 'ja' ? i.labelJa : i.labelEn}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* legend */}
        <div className={s.legend}>
          {['2026–2050', '2051–2075', '2076–2100'].map((label, i) => (
            <span key={i} className={s.legendItem}>
              <span className={s.legendDot} style={{ background: CYCLE_COLORS[i] }} />
              {label}
            </span>
          ))}
        </div>

        <div className={s.chartWrap}>
          {scatterData.length === 0 ? (
            <div className={s.empty}>{t('analysis.scatter.empty')}</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="x" type="number" tickFormatter={fmtY} tick={{ fontSize: 11 }} domain={['auto', 'auto']}>
                  <Label
                    value={lang === 'ja' ? xInd?.labelJa : xInd?.labelEn}
                    position="insideBottom" offset={-18}
                    style={{ fontSize: 11, fill: '#888' }}
                  />
                </XAxis>
                <YAxis dataKey="y" type="number" tickFormatter={fmtY} tick={{ fontSize: 11 }} width={58}>
                  <Label
                    value={lang === 'ja' ? yInd?.labelJa : yInd?.labelEn}
                    angle={-90} position="insideLeft" offset={18}
                    style={{ fontSize: 11, fill: '#888' }}
                  />
                </YAxis>
                <Tooltip
                  cursor={{ strokeDasharray: '3 3' }}
                  content={({ payload }) => {
                    if (!payload?.length) return null
                    const d = payload[0].payload
                    return (
                      <div className={s.tooltip}>
                        <div className={s.tooltipYear}>YEAR {d.year}</div>
                        <div>{lang === 'ja' ? xInd?.labelJa : xInd?.labelEn}: {fmtY(d.x)}</div>
                        <div>{lang === 'ja' ? yInd?.labelJa : yInd?.labelEn}: {fmtY(d.y)}</div>
                      </div>
                    )
                  }}
                />
                <Scatter data={scatterData} shape={<CustomDot />} />
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

    </div>
  )
}
