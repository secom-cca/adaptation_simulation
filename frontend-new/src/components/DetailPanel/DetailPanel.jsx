import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { CHART_KEYS, fmtY } from '../../data/indicators.js'
import s from './DetailPanel.module.css'

const CLIMATE_INDICATOR_KEYS = new Set([
  'Temperature (°C)',
  'Precipitation (mm)',
  'Extreme Precip Frequency',
])

export default function DetailPanel({
  history,
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
  onRequestResidentInterview,
  onSelectIndicator,
  rcpValue,
  rightInset = false,
}) {
  const { t, lang } = useTranslation()
  const [activeOutcomeKey, setActiveOutcomeKey] = useState('Flood Damage JPY')
  const [activeClimateKey, setActiveClimateKey] = useState('Temperature (°C)')

  const lowByYear = new Map((sensitivityHistories[1.9] ?? []).map(row => [row.year, row]))
  const highByYear = new Map((sensitivityHistories[8.5] ?? []).map(row => [row.year, row]))
  const outcomeIndicators = CHART_KEYS.filter(indicator => !CLIMATE_INDICATOR_KEYS.has(indicator.key))
  const climateIndicators = CHART_KEYS.filter(indicator => CLIMATE_INDICATOR_KEYS.has(indicator.key))

  const renderIndicatorChip = (indicator, activeKey, setActiveKey) => (
    <button key={indicator.key} className={`${s.chip} ${activeKey === indicator.key ? s.chipActive : ''}`}
      style={activeKey === indicator.key ? { borderColor: indicator.color, color: indicator.color, background: `${indicator.color}12` } : {}}
      onClick={() => {
        setActiveKey(indicator.key)
        onSelectIndicator?.(indicator.key)
      }}>
      {lang === 'ja' ? indicator.labelJa : indicator.labelEn}
    </button>
  )

  const renderTimeSeriesChart = (activeKey) => {
    const activeIndicator = CHART_KEYS.find(indicator => indicator.key === activeKey)
    const activeLabel = lang === 'ja' ? activeIndicator?.labelJa : activeIndicator?.labelEn
    const chartData = history.map(row => ({
      year: row.year,
      value: row[activeKey] ?? 0,
      low: lowByYear.get(row.year)?.[activeKey] ?? null,
      high: highByYear.get(row.year)?.[activeKey] ?? null,
    }))

    if (chartData.length === 0) return <div className={s.empty}>{t('detail.chart.empty')}</div>

    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="year" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} width={70} tickFormatter={fmtY} />
          <Tooltip
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
            formatter={value => [typeof value === 'number' ? fmtY(value) : value, activeLabel]}
          />
          <Line type="monotone" dataKey="value" stroke={activeIndicator?.color ?? '#888'}
            name={scenarioLabel} strokeWidth={3} dot={false} activeDot={{ r: 4 }} />
          {rcpValue === 'composite' && <Line type="monotone" dataKey="low" name="RCP1.9" stroke="#6f9fc8" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />}
          {rcpValue === 'composite' && <Line type="monotone" dataKey="high" name="RCP8.5" stroke="#c77a68" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const residents = residentCouncil?.residents ?? []
  const latestRows = history.slice(-25)
  const periodSummary = {
    flood: latestRows.reduce((sum, row) => sum + (Number(row['Flood Damage JPY']) || 0), 0),
    crop: latestRows.length ? latestRows.reduce((sum, row) => sum + (Number(row['Crop Yield']) || 0), 0) / latestRows.length : 0,
    ecosystem: latestRows.length ? latestRows.reduce((sum, row) => sum + (Number(row['Ecosystem Level']) || 0), 0) / latestRows.length : 0,
  }
  const scenarioLabel = rcpValue === 'composite' ? 'RCP4.5' : `RCP${rcpValue}`
  return (
    <div className={`${s.grid} ${rightInset ? s.withRightInset : ''}`}>
      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.chart.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.chart.sub')}</span>
        </div>
        <div className={s.chartStack}>
          <section className={s.chartSection}>
            <div className={s.chipRow}>
              <span className={s.chipGroupLabel}>{lang === 'ja' ? '結果・状態' : 'OUTCOME & STATE'}</span>
              {outcomeIndicators.map(indicator => renderIndicatorChip(indicator, activeOutcomeKey, setActiveOutcomeKey))}
            </div>
            <div className={s.chartWrap}>
              {renderTimeSeriesChart(activeOutcomeKey)}
            </div>
          </section>
          <section className={s.chartSection}>
            <div className={s.chipRow}>
              <span className={s.chipGroupLabel}>{lang === 'ja' ? '気候' : 'CLIMATE'}</span>
              {climateIndicators.map(indicator => renderIndicatorChip(indicator, activeClimateKey, setActiveClimateKey))}
            </div>
            <div className={s.chartWrap}>
              {renderTimeSeriesChart(activeClimateKey)}
            </div>
          </section>
        </div>
      </div>

      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.sns.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.sns.sub')}</span>
        </div>
        <div className={s.snsList}>
          {history.length === 0 && <div className={s.empty}>{t('detail.sns.empty')}</div>}
          {history.length > 0 && residentCouncilLoading && <div className={s.empty}>{t('detail.sns.loading')}</div>}
          {history.length > 0 && !residentCouncilLoading && residentCouncilError && (
            <div className={s.empty}>{t('detail.sns.error')}</div>
          )}
          {history.length > 0 && !residentCouncilLoading && !residentCouncilError && residents.length === 0 && (
            <div className={s.empty}>{t('detail.sns.empty')}</div>
          )}
          {history.length > 0 && !residentCouncilLoading && !residentCouncilError && residents.map(resident => {
            const detail = residentInterviews[resident.persona_key]
            const loadingDetail = residentInterviewLoading[resident.persona_key]
            return (
              <div key={resident.persona_key} className={s.snsPost}>
                <span className={s.snsAvatar}>{resident.avatar}</span>
                <div className={s.snsBody}>
                  <div className={s.snsUserRow}>
                    <div className={s.snsUser}>{resident.display_name} <span>{resident.handle}</span></div>
                    <StarRating score={resident.score} lang={lang} />
                  </div>
                  <div className={s.snsText}>{resident.short_voice}</div>
                  <div className={s.snsMeta}>{resident.focus}</div>
                  {detail && <div className={s.interviewText}>{detail}</div>}
                  <button
                    type="button"
                    className={s.detailButton}
                    disabled={loadingDetail}
                    onClick={() => onRequestResidentInterview?.(resident.persona_key, resident.score)}
                  >
                    {loadingDetail ? t('detail.sns.detail_loading') : t('detail.sns.detail')}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
        {latestRows.length > 0 && <div className={s.periodSummary}>
          <strong>{year - 25}–{year - 1} 実績</strong>
          <span>洪水被害額（25年累計）<b>{(periodSummary.flood / 100_000_000).toLocaleString(undefined, { maximumFractionDigits: 2 })} 億円</b></span>
          <span>農作物生産高（25年平均）<b>{periodSummary.crop.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg/ha</b></span>
          <span>生態系（25年平均）<b>{periodSummary.ecosystem.toLocaleString(undefined, { maximumFractionDigits: 1 })} %</b></span>
        </div>}
      </div>
    </div>
  )
}

function getScoreBadgeClass(score) {
  const value = Number(score)
  if (Number.isNaN(value)) return ''
  if (value <= 3) return s.scoreLow
  if (value <= 6) return s.scoreMedium
  return s.scoreHigh
}

function StarRating({ score, lang }) {
  const numericScore = Number(score)
  const rating = Number.isFinite(numericScore)
    ? Math.max(0, Math.min(5, numericScore / 2))
    : 0
  const ratingLabel = Number.isInteger(rating) ? String(rating) : rating.toFixed(1)
  const ariaLabel = lang === 'ja'
    ? `5つ星中${ratingLabel}`
    : `${ratingLabel} out of 5 stars`

  return (
    <div className={`${s.scoreBadge} ${getScoreBadgeClass(score)}`} aria-label={ariaLabel} title={ariaLabel}>
      <span className={s.starRating} aria-hidden="true">
        <span className={s.starEmpty}>★★★★★</span>
        <span className={s.starFill} style={{ width: `${rating * 20}%` }}>★★★★★</span>
      </span>
      <span className={s.ratingValue}>{ratingLabel}/5</span>
    </div>
  )
}

function AiEvaluationArticle({ article, t }) {
  return (
    <div className={s.newspaperPanel}>
      {(article.headline || article.subheadline || article.lead) && (
        <div className={s.articleIntro}>
          {article.headline && <h3>{article.headline}</h3>}
          {article.subheadline && <p className={s.articleSubheadline}>{article.subheadline}</p>}
          {article.lead && <p className={s.articleLead}>{article.lead}</p>}
        </div>
      )}
      {article.policyAssessment && (
        <div className={s.policyStrip}>
          <span>{t('detail.llm.policy')}</span>
          <strong>{article.policyAssessment}</strong>
        </div>
      )}
      <div className={s.articleFlow}>
        {article.body.length > 0 && (
          <div className={s.articleBody}>
            {article.body.map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>
        )}
        {article.expertComment && (
          <aside className={s.expertBox}>
            <div>{t('detail.llm.comment')}</div>
            <p>{article.expertComment}</p>
          </aside>
        )}
      </div>
    </div>
  )
}

function parseAiEvaluation(text = '') {
  const fields = {
    headline: '',
    subheadline: '',
    lead: '',
    policyAssessment: '',
    expertComment: '',
    body: [],
  }
  const bodyLines = []
  const keyMap = {
    '見出し': 'headline',
    'サブ見出し': 'subheadline',
    'リード': 'lead',
    '政策評価': 'policyAssessment',
    'コメント': 'expertComment',
    '本文': 'body',
    'headline': 'headline',
    'subheadline': 'subheadline',
    'lead': 'lead',
    'policy assessment': 'policyAssessment',
    'policy_assessment': 'policyAssessment',
    'expert comment': 'expertComment',
    'expert_comment': 'expertComment',
    'article body': 'body',
    'article_body': 'body',
    'body': 'body',
  }

  for (const rawLine of String(text).split('\n')) {
    const line = rawLine.trim()
    if (!line) {
      if (bodyLines.length && bodyLines[bodyLines.length - 1] !== '') bodyLines.push('')
      continue
    }

    const match = line.match(/^([^:：]+)[:：]\s*(.*)$/)
    const keyName = match ? match[1].trim().replace(/^["']|["']$/g, '').toLowerCase() : ''
    const key = keyName ? keyMap[keyName] : null
    if (key) {
      if (key === 'body') {
        if (match[2].trim()) bodyLines.push(match[2].trim())
        continue
      }
      fields[key] = match[2].trim()
      continue
    }
    bodyLines.push(line)
  }

  fields.body = bodyLines
    .join('\n')
    .split(/\n{2,}/)
    .map(part => part.replace(/\n/g, ' ').trim())
    .filter(Boolean)

  const hasStructuredFields = Boolean(
    fields.headline || fields.subheadline || fields.lead || fields.policyAssessment || fields.expertComment,
  )

  if (fields.body.length === 0 && text && !hasStructuredFields) {
    fields.body = String(text)
      .split('\n')
      .map(line => line.trim())
      .map(line => line.replace(/^(見出し|サブ見出し|リード|Headline|Subheadline|Lead)[:：]\s*/i, '').trim())
      .filter(Boolean)
  }

  return fields
}

function getEvents(history, t) {
  const events = []
  history.forEach(row => {
    const backendEvents = Array.isArray(row.events) ? row.events : (Array.isArray(row.Events) ? row.Events : [])
    backendEvents.forEach(ev => {
      const normalized = normalizeBackendEvent(ev)
      if (!normalized) return
      events.push({
        year: ev.year ?? row.year,
        ...normalized,
      })
    })
    const floodJpy = row['Flood Damage JPY'] ?? ((row['Flood Damage'] ?? 0) * 150)
    if (floodJpy > 100_000_000) {
      events.push({ year: row.year, icon: '🌊', title: t('event.flood'), body: formatJpy(floodJpy), category: 'Flood', severity: 'warn' })
    }
    if ((row['Crop Yield'] ?? 5000) < 3000) {
      events.push({ year: row.year, icon: '🌾', title: t('event.crop'), body: '高温や水害の影響で食糧生産が下がっています。', category: 'Food', severity: 'warn' })
    }
    if ((row['Ecosystem Level'] ?? 100) < 40) {
      events.push({ year: row.year, icon: '🌿', title: t('event.eco'), body: '生態系指標が低下しています。治水と自然環境のバランスに注意が必要です。', category: 'Eco', severity: 'critical' })
    }
  })
  if (events.length === 0) {
    events.push({ year: '-', icon: '✓', title: t('event.none'), body: 'この期間は大きな閾値イベントはありません。', category: 'Status', severity: 'ok' })
  }
  return events.slice(-12)
}

function formatJpy(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `被害額 約${(amount / 100_000_000).toFixed(1)}億円。`
  if (amount >= 10_000) return `被害額 約${Math.round(amount / 10_000).toLocaleString()}万円。`
  return `被害額 約${Math.round(amount).toLocaleString()}円。`
}

function normalizeBackendEvent(ev) {
  if (ev.category === 'urban') return null
  const valueText = ev.metric?.includes('Damage') ? ` ${formatJpy(ev.value)}` : ''
  return {
    icon: eventIcon(ev.category),
    title: ev.title ?? 'イベント',
    body: `${valueText}${ev.message ?? ''}`.trim(),
    category: categoryLabel(ev.category),
    severity: ev.severity === 'critical' ? 'critical' : ev.severity === 'success' ? 'ok' : 'warn',
  }
}

function eventIcon(category) {
  if (category === 'flood' || category === 'climate') return '🌊'
  if (category === 'agriculture') return '🌾'
  if (category === 'ecosystem') return '🌿'
  if (category === 'budget') return '💴'
  if (category === 'resident') return '🏘️'
  if (category === 'policy_effect') return '✓'
  return '!'
}

function categoryLabel(category) {
  if (category === 'flood') return 'Flood'
  if (category === 'climate') return 'Rain'
  if (category === 'agriculture') return 'Food'
  if (category === 'ecosystem') return 'Eco'
  if (category === 'budget') return 'Budget'
  if (category === 'resident') return 'Resident'
  if (category === 'policy_effect') return 'Policy'
  return 'Event'
}
