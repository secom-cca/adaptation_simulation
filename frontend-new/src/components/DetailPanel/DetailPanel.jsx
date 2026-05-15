import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { CHART_KEYS, fmtY } from '../../data/indicators.js'
import s from './DetailPanel.module.css'

export default function DetailPanel({
  history,
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
}) {
  const { t, lang } = useTranslation()
  const [activeKey, setActiveKey] = useState('Flood Damage JPY')

  const chartData = history.map(row => ({ year: row.year, value: row[activeKey] ?? 0 }))
  const activeInd = CHART_KEYS.find(i => i.key === activeKey)
  const activeLabel = lang === 'ja' ? activeInd?.labelJa : activeInd?.labelEn

  const residents = residentCouncil?.residents ?? []
  const article = parseAiEvaluation(llmCommentary)

  return (
    <div className={s.grid}>
      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.chart.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.chart.sub')}</span>
        </div>
        <div className={s.chipRow}>
          <span className={s.chipGroupLabel}>{lang === 'ja' ? '結果' : 'OUTCOME'}</span>
          {CHART_KEYS.map(i => (
            <button key={i.key} className={`${s.chip} ${activeKey === i.key ? s.chipActive : ''}`}
              style={activeKey === i.key ? { borderColor: i.color, color: i.color, background: `${i.color}12` } : {}}
              onClick={() => setActiveKey(i.key)}>
              {lang === 'ja' ? i.labelJa : i.labelEn}
            </button>
          ))}
        </div>
        <div className={s.chartWrap}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={fmtY} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={v => [typeof v === 'number' ? fmtY(v) : v, activeLabel]}
                />
                <Line type="monotone" dataKey="value" stroke={activeInd?.color ?? '#888'}
                  strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className={s.empty}>{t('detail.chart.empty')}</div>
          )}
        </div>
      </div>

      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.llm.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.llm.sub')}</span>
          <span className={s.badge}>{t('detail.llm.badge')}</span>
        </div>
        <div className={s.llmBody}>
          {history.length === 0 && <div className={s.empty}>{t('detail.llm.empty')}</div>}
          {history.length > 0 && llmLoading && <div className={s.empty}>{t('detail.llm.loading')}</div>}
          {history.length > 0 && !llmLoading && llmCommentary && (
            <AiEvaluationArticle article={article} t={t} />
          )}
          {history.length > 0 && !llmLoading && !llmCommentary && (
            <div className={s.empty}>{t('detail.llm.error')}</div>
          )}
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
                    <div className={`${s.scoreBadge} ${getScoreBadgeClass(resident.score)}`}>{resident.score}/10</div>
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
