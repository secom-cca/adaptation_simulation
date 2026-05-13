import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { CHART_KEYS, fmtY } from '../../data/indicators.js'
import s from './DetailPanel.module.css'

const SNS_POSTS = [
  { avatar: '上', userEn: '@tanaka_upstream', userJa: '@tanaka_upstream', postKey: 'sns.post.1', likes: 34, time: '2h' },
  { avatar: '森', userEn: '@eco_watcher', userJa: '@eco_watcher', postKey: 'sns.post.2', likes: 87, time: '5h' },
  { avatar: '庁', userEn: '@mayor_office', userJa: '@mayor_office', postKey: 'sns.post.3', likes: 12, time: '8h' },
  { avatar: '住', userEn: '@young_resident', userJa: '@young_resident', postKey: 'sns.post.4', likes: 56, time: '10h' },
]

export default function DetailPanel({ history, currentValues, cycle, year }) {
  const { t, lang } = useTranslation()
  const [activeKey, setActiveKey] = useState('Flood Damage JPY')

  const chartData = history.map(row => ({ year: row.year, value: row[activeKey] ?? 0 }))
  const activeInd = CHART_KEYS.find(i => i.key === activeKey)
  const activeLabel = lang === 'ja' ? activeInd?.labelJa : activeInd?.labelEn

  const cycleStart = year - 25
  const llmText = (t('llm.placeholder') || '')
    .replace('{cycle}', String(Math.max(cycle - 1, 1)))
    .replace('{startYear}', String(cycleStart))
    .replace('{endYear}', String(year))

  const events = getRichEvents(history, t)

  return (
    <div className={s.grid}>
      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.chart.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.chart.sub')}</span>
        </div>
        <div className={s.chipRow}>
          <span className={s.chipGroupLabel}>{lang === 'ja' ? '結果' : 'OUTCOME'}</span>
          {CHART_KEYS.slice(0, 5).map(i => (
            <button key={i.key} className={`${s.chip} ${activeKey === i.key ? s.chipActive : ''}`}
              style={activeKey === i.key ? { borderColor: i.color, color: i.color, background: `${i.color}12` } : {}}
              onClick={() => setActiveKey(i.key)}>
              {lang === 'ja' ? i.labelJa : i.labelEn}
            </button>
          ))}
          <span className={s.chipDivider} />
          <span className={s.chipGroupLabel}>{lang === 'ja' ? '気候' : 'CLIMATE'}</span>
          {CHART_KEYS.slice(5, 8).map(i => (
            <button key={i.key} className={`${s.chip} ${activeKey === i.key ? s.chipActive : ''}`}
              style={activeKey === i.key ? { borderColor: i.color, color: i.color, background: `${i.color}12` } : {}}
              onClick={() => setActiveKey(i.key)}>
              {lang === 'ja' ? i.labelJa : i.labelEn}
            </button>
          ))}
          <span className={s.chipDivider} />
          <span className={s.chipGroupLabel}>{lang === 'ja' ? '中間' : 'INTERMEDIATE'}</span>
          {CHART_KEYS.slice(8).map(i => (
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
          {history.length === 0
            ? <div className={s.empty}>{t('detail.llm.empty')}</div>
            : <pre className={s.llmText}>{llmText}</pre>
          }
        </div>
      </div>

      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.events.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.events.sub')}</span>
        </div>
        <div className={s.eventList}>
          {events.length === 0
            ? <div className={s.empty}>{t('detail.events.empty')}</div>
            : events.map((ev, i) => (
              <div key={i} className={`${s.eventCard} ${s[ev.severity]}`}>
                <div className={s.eventCardTop}>
                  <span className={s.eventIcon}>{ev.icon}</span>
                  <span className={s.eventYear}>{ev.year}</span>
                  {ev.category && <span className={s.eventCategory}>{ev.category}</span>}
                </div>
                <div className={s.eventTitle}>{ev.title}</div>
                <div className={s.eventText}>{ev.body}</div>
              </div>
            ))
          }
        </div>
      </div>

      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.sns.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.sns.sub')}</span>
        </div>
        <div className={s.snsList}>
          {SNS_POSTS.map((post, i) => (
            <div key={i} className={s.snsPost}>
              <span className={s.snsAvatar}>{post.avatar}</span>
              <div className={s.snsBody}>
                <div className={s.snsUser}>{lang === 'ja' ? post.userJa : post.userEn}</div>
                <div className={s.snsText}>{t(post.postKey)}</div>
                <div className={s.snsMeta}>♥ {post.likes} · {post.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function getRichEvents(history, t) {
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
