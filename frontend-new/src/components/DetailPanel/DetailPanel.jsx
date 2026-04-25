import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import { CHART_KEYS, fmtY } from '../../data/indicators.js'
import s from './DetailPanel.module.css'

const SNS_POSTS = [
  { avatar: '🧑‍🌾', userEn: '@tanaka_upstream',  userJa: '@tanaka_upstream',  postKey: 'sns.post.1', likes: 34, time: '2h' },
  { avatar: '🌿',   userEn: '@eco_watcher',       userJa: '@eco_watcher',      postKey: 'sns.post.2', likes: 87, time: '5h' },
  { avatar: '🏛',   userEn: '@mayor_office',      userJa: '@mayor_office',     postKey: 'sns.post.3', likes: 12, time: '8h' },
  { avatar: '👩‍🎓', userEn: '@young_resident',    userJa: '@young_resident',   postKey: 'sns.post.4', likes: 56, time: '10h' },
]

export default function DetailPanel({ history, currentValues, cycle, year }) {
  const { t, lang } = useTranslation()
  const [activeKey, setActiveKey] = useState('Flood Damage')

  const chartData = history.map(row => ({ year: row.year, value: row[activeKey] ?? 0 }))
  const activeInd = CHART_KEYS.find(i => i.key === activeKey)
  const activeLabel = lang === 'ja' ? activeInd?.labelJa : activeInd?.labelEn

  const cycleStart = year - 25
  const llmText = (t('llm.placeholder') || '')
    .replace('{cycle}', String(Math.max(cycle - 1, 1)))
    .replace('{startYear}', String(cycleStart))
    .replace('{endYear}', String(year))

  const events = getEvents(history, t)

  return (
    <div className={s.grid}>

      {/* ── Top-left: Chart ── */}
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
                <YAxis tick={{ fontSize: 11 }} width={55} tickFormatter={fmtY} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  formatter={v => [typeof v === 'number' ? v.toFixed(2) : v, activeLabel]}
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

      {/* ── Top-right: LLM ── */}
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

      {/* ── Bottom-left: Events ── */}
      <div className={s.cell}>
        <div className={s.cellHeader}>
          <span className={s.cellTitle}>{t('detail.events.title')}</span>
          <span className={s.cellSubtitle}>{t('detail.events.sub')}</span>
        </div>
        <div className={s.eventList}>
          {events.length === 0
            ? <div className={s.empty}>{t('detail.events.empty')}</div>
            : events.map((ev, i) => (
              <div key={i} className={`${s.eventRow} ${s[ev.severity]}`}>
                <span className={s.eventYear}>{ev.year}</span>
                <span className={s.eventIcon}>{ev.icon}</span>
                <span className={s.eventText}>{ev.text}</span>
              </div>
            ))
          }
        </div>
      </div>

      {/* ── Bottom-right: SNS ── */}
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

function getEvents(history, t) {
  const events = []
  history.forEach(row => {
    if ((row['Flood Damage'] ?? 0) > 1e7)
      events.push({ year: row.year, icon: '🌊', text: t('event.flood'), severity: 'warn' })
    if ((row['Crop Yield'] ?? 5000) < 3000)
      events.push({ year: row.year, icon: '🌾', text: t('event.crop'), severity: 'warn' })
    if ((row['Ecosystem Level'] ?? 100) < 40)
      events.push({ year: row.year, icon: '🌿', text: t('event.eco'), severity: 'critical' })
  })
  if (events.length === 0)
    events.push({ year: '—', icon: '✅', text: t('event.none'), severity: 'ok' })
  return events.slice(-12)
}
