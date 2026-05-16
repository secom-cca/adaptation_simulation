import React from 'react'
import { useTranslation } from '../../contexts/LanguageContext.jsx'
import s from './ScenarioBriefing.module.css'

const DOMAIN_COLORS = {
  洪水: '#3d6b8f',
  農業: '#4a8c5c',
  生態系: '#6b8c3d',
  予算: '#8c6b3d',
  生活: '#7a4a8c',
  Flood: '#3d6b8f',
  Agriculture: '#4a8c5c',
  Ecology: '#6b8c3d',
  Budget: '#8c6b3d',
  Livelihood: '#7a4a8c',
}

const BRIEFINGS = [
  {
    years: '2026-2050',
    titleJa: '初期投資の方向性',
    titleEn: 'Early investment direction',
    bodyJa: 'この期間は、将来の被害を左右する基盤づくりの時期です。森林、堤防、田んぼダム、住宅移転、防災訓練、農業R&Dの条件を見ながら、治水対策や被害を軽減するための対策を取る必要があります。',
    bodyEn: 'This period sets the foundation for future damage reduction. Watch forest, levee, paddy dam, relocation, preparedness, and agriculture R&D conditions, then invest in flood control and damage-reduction measures.',
    domainsJa: ['洪水', '農業'],
    domainsEn: ['Flood', 'Agriculture'],
  },
  {
    years: '2051-2075',
    titleJa: '効果の差が見え始める期間',
    titleEn: 'Policy effects begin to diverge',
    bodyJa: '気温上昇と強い雨の影響が大きくなり、前半の投資の差が結果に表れ始めます。農作物生産や生態系の変化も確認しながら、治水対策や被害を軽減するための対策を取る必要があります。',
    bodyEn: 'Warming and heavy rainfall pressure increase, and early choices begin to show in the outcomes. Check crop and ecosystem conditions while strengthening flood control and damage-reduction measures.',
    domainsJa: ['農業', '生態系'],
    domainsEn: ['Agriculture', 'Ecology'],
  },
  {
    years: '2076-2100',
    titleJa: '最終結果を決める調整期間',
    titleEn: 'Final adjustment period',
    bodyJa: '人口減少による予算制約、洪水被害、農作物生産、生態系の状態を同時に見て、最後の配分を決める期間です。残った弱点に対して、治水対策や被害を軽減するための対策を取る必要があります。',
    bodyEn: 'This is the final allocation period, with budget constraints, flood damage, crop production, and ecosystem conditions all in view. Address the remaining weaknesses with flood control and damage-reduction measures.',
    domainsJa: ['洪水', '予算', '生活'],
    domainsEn: ['Flood', 'Budget', 'Livelihood'],
  },
]

function briefingIndex(year, cycle) {
  if (year <= 2050) return 0
  if (year <= 2075) return 1
  if (year <= 2100) return 2
  return Math.min(Math.max((cycle ?? 1) - 1, 0), 2)
}

export default function ScenarioBriefing({ year, cycle }) {
  const { lang } = useTranslation()
  const briefing = BRIEFINGS[briefingIndex(year, cycle)]
  const domains = lang === 'ja' ? briefing.domainsJa : briefing.domainsEn

  return (
    <div className={s.card}>
      <div className={s.header}>{lang === 'ja' ? '期間シナリオ' : 'Period scenario'}</div>
      <h3 className={s.title}>{briefing.years} {lang === 'ja' ? briefing.titleJa : briefing.titleEn}</h3>
      <p className={s.body}>{lang === 'ja' ? briefing.bodyJa : briefing.bodyEn}</p>
      <div className={s.domainRow}>
        <span className={s.domainLabel}>{lang === 'ja' ? '注目条件' : 'Focus'}</span>
        <div className={s.tags}>
          {domains.map(d => (
            <span
              key={d}
              className={s.tag}
              style={{ background: `${DOMAIN_COLORS[d] ?? '#888'}22`, color: DOMAIN_COLORS[d] ?? '#888' }}
            >
              {d}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
