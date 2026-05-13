import React, { createContext, useContext, useState } from 'react'

const LanguageContext = createContext({ lang: 'ja', toggle: () => {} })

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState('ja')
  const toggle = () => setLang(l => l === 'ja' ? 'en' : 'ja')
  return (
    <LanguageContext.Provider value={{ lang, toggle }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useTranslation() {
  const { lang, toggle } = useContext(LanguageContext)
  const t = (key) => T[lang]?.[key] ?? T.en?.[key] ?? key
  return { t, lang, toggle }
}

// ── All UI strings ──────────────────────────────────────────────────
const T = {
  en: {
    // EntryPage
    'entry.subtitle':      'Choose policies from 2026 to 2100 to protect your river basin community from climate change.',
    'entry.username':      'Username',
    'entry.username.ph':   'Your name',
    'entry.team':          'Team Name (optional)',
    'entry.team.ph':       'Team name (optional)',
    'entry.mode.label':    'Region Mode',
    'entry.upstream.name': 'Upstream',
    'entry.upstream.desc': 'Forest · Levee · Paddy Dam',
    'entry.downstream.name': 'Downstream',
    'entry.downstream.desc': 'Levee · Relocation · Training',
    'entry.team.name':     'Team',
    'entry.team.desc':     'Upstream + Downstream · All 6 policies',
    'entry.rcp.label':     'Climate Scenario (RCP)',
    'entry.start':         'Start Simulation',
    'rcp.1.9.desc':        'Strong mitigation',
    'rcp.2.6.desc':        'Moderate mitigation',
    'rcp.4.5.desc':        'Intermediate',
    'rcp.6.0.desc':        'High emissions',
    'rcp.8.5.desc':        'Very high emissions',

    // TopBar
    'topbar.simple':    '🗺 Overview',
    'topbar.detail':    '📊 Detail',
    'topbar.analysis':  '🔬 Analysis',
    'topbar.upstream':  'UPSTREAM',
    'topbar.downstream':'DOWNSTREAM',
    'topbar.team':      'TEAM',

    // CycleReport
    'report.subtitle': 'CYCLE {n} — 25-YEAR REPORT',
    'report.title':    '25-Year Report Generated',
    'report.flood':    'Flood Damage',
    'report.crop':     'Crop Yield',
    'report.eco':      'Ecosystem',
    'report.burden':   'Resident Burden',
    'report.cta':         'View Details →',
    'report.llm_title':   'AI Policy Analysis',
    'report.llm_loading': 'Generating analysis…',

    // AnalysisPage
    'analysis.cld.title':      'System Dynamics Model',
    'analysis.cld.sub':        'CAUSAL STRUCTURE',
    'analysis.scatter.title':  'Policy × Outcome',
    'analysis.scatter.sub':    'SCATTER PLOT',
    'analysis.scatter.x':      'X',
    'analysis.scatter.y':      'Y',
    'analysis.scatter.empty':  'Run a simulation cycle to see data',

    // BasinStatus
    'basin.header':          'BASIN STATUS',
    'basin.flood.label':     'Flood Risk',
    'basin.food.label':      'Food Production',
    'basin.burden.label':    'Resident Burden',
    'basin.eco.label':       'Ecosystem',
    'status.low':            'Low',
    'status.medium':         'Medium',
    'status.high':           'High',
    'status.stable':         'Stable',
    'status.declining':      'Declining',
    'status.critical':       'Critical',
    'status.manageable':     'Manageable',
    'status.elevated':       'Elevated',
    'status.severe':         'Severe',
    'status.healthy':        'Healthy',
    'status.stressed':       'Stressed',
    'status.degraded':       'Degraded',
    'budget.appliedFloodDamage': 'Flood damage used',
    'budget.pointReduction':     'Budget reduction',
    'budget.availablePoints':    'Available points',
    'budget.floodShort':         'flood',
    'budget.relocationShort':    'relocation',
    'budget.ruleNote':           'Budget decreases according to population decline, average flood damage in the previous 25 years, and relocation-related infrastructure costs.',

    // ScenarioBriefing
    'briefing.header': '⚠ SCENARIO BRIEFING',
    'briefing.domains.label': 'AFFECTED DOMAINS',
    'briefing.1.title': 'Extreme rainfall probability increases this period',
    'briefing.1.body':  'Climate models project a 40% increase in heavy precipitation events over the next 25-year cycle, with cascading effects on infrastructure and agriculture.',
    'briefing.2.title': 'Heat stress accelerating crop yield decline',
    'briefing.2.body':  'Average temperatures are expected to rise 1.2°C above the 2026 baseline. Without adaptation, crop yields may fall below sustainable thresholds by 2075.',
    'briefing.3.title': 'Final phase: compounding risks peak',
    'briefing.3.body':  'Flood frequency, heat stress, and demographic pressure converge. Policy decisions made now will determine the long-term trajectory of this community.',

    // DetailPanel
    'detail.chart.title':   'Indicators Over Time',
    'detail.chart.sub':     'INDICATORS OVER TIME',
    'detail.llm.title':     'AI Evaluation',
    'detail.llm.sub':       'LLM COMMENTARY',
    'detail.llm.badge':     'CONNECTED',
    'detail.events.title':  'Event Log',
    'detail.events.sub':    'EVENT LOG',
    'detail.sns.title':     'Resident Reactions',
    'detail.sns.sub':       'RESIDENT VOICES',
    'detail.chart.empty':   'Advance the simulation to view charts',
    'detail.llm.empty':     'AI commentary will appear after each cycle',
    'detail.llm.loading':   'Generating AI evaluation...',
    'detail.llm.error':     'AI evaluation could not be generated.',
    'detail.llm.policy':    'POLICY READ',
    'detail.llm.comment':   'EXPERT VIEW',
    'detail.events.empty':  'No events yet',
    'detail.sns.empty':     'Resident reactions will appear after each cycle',
    'detail.sns.loading':   'Generating resident reactions...',
    'detail.sns.error':     'Resident reactions could not be generated.',
    'detail.sns.detail':    'Details',
    'detail.sns.detail_loading': 'Interviewing...',
    'event.flood':          'Flood damage occurred',
    'event.crop':           'Crop yield declining',
    'event.eco':            'Ecosystem stress detected',
    'event.none':           'No major events this period',
    'sns.post.1':           'Worried about flooding again this year… when will the levee work be done?',
    'sns.post.2':           'Ecosystem index is improving. Forest policy might be taking effect!',
    'sns.post.3':           'Fiscal report: infrastructure investment is on track. We continue to monitor.',
    'sns.post.4':           'More R&D investment! Good call for the future. But don\'t forget today\'s farmers.',

    // LLM placeholder
    'llm.placeholder':
`[AI Evaluation — Cycle {cycle} ({startYear}–{endYear})]

Comprehensive assessment of this cycle's policy choices.

Regarding flood risk: levee investment levels are within an appropriate range, providing reasonable defense against increasing precipitation trends. However, if extreme precipitation frequency continues rising, current levee capacity may reach critical limits.

On agriculture: R&D investment in heat-tolerant crops is ongoing, though benefits take decades to materialize. Additional measures to counter mid-term yield decline are recommended.

Ecosystem indicators show stable conditions, but sustained forest investment is essential for long-term improvement.

Overall Grade: B+`,

    // DecisionPanel
    'decision.title':    'Policy Selection',
    'decision.sub':      'POLICY DECISIONS',
    'decision.advance':  'Advance 25 Years ›',
    'decision.loading':  'Running…',
    'decision.expand':   'Expand',
    'decision.collapse': 'Collapse',

    // PolicySlider tiers
    'tier.weak':     'Weak',
    'tier.standard': 'Standard',
    'tier.strong':   'Strong',

    // Event pages (consequence + exogenous)
    'consequence.continue':     'Continue →',
    'event.tag.random':         'RANDOM EVENT',
    'event.flood.subtitle':     'RIVER FLOODING',
    'event.flood.title':        'River Flooding',
    'event.flood.body':         'This 25-year period included a large flood with damage of {amount}. In the model, this represents damage to housing, farmland, businesses, roads, and public facilities. Part of this damage reduces the next policy budget as recovery, waste removal, evacuation support, and rebuilding work.',
    'event.drought.subtitle':   'CROP FAILURE',
    'event.drought.title':      'Heat-Driven Harvest Collapse',
    'event.drought.body':       'Crop yield has fallen below a critical level. In this model, heat stress, water shortage, and flood damage can reduce food production. Agricultural R&D improves heat tolerance, but its effect appears only after accumulated investment.',
    'event.wq.subtitle':        'WATER QUALITY CRISIS',
    'event.wq.title':           'River Quality Deterioration',
    'event.wq.body':            'The ecosystem indicator has fallen below a critical level. In this model, water availability, forest condition, and infrastructure pressure interact, so flood control and ecosystem recovery need to be balanced.',
    'event.ls.subtitle':        'MODEL EVENT',
    'event.ls.title':           'Model threshold reached',
    'event.ls.body':            'A model threshold has been reached. Review flood damage, food production, ecosystem level, and budget burden before the next allocation.',
    'event.wf.subtitle':        'MODEL EVENT',
    'event.wf.title':           'Model threshold reached',
    'event.wf.body':            'A model threshold has been reached. Review flood damage, food production, ecosystem level, and budget burden before the next allocation.',
    'event.tb.subtitle':        'RANDOM EVENT — BREAKTHROUGH',
    'event.tb.title':           'Agricultural Technology Breakthrough',
    'event.tb.body':            'A new heat-tolerant crop variety has been successfully developed. Heat tolerance has improved and additional water reserves have been secured for the next cycle.',

    // GamePage goals
    'goal.upstream.1': 'Control flood risk while maintaining ecosystem health',
    'goal.upstream.2': 'Balance forest expansion with fiscal sustainability',
    'goal.upstream.3': 'Secure long-term watershed resilience',
    'goal.downstream.1': 'Reduce resident exposure to flood risk',
    'goal.downstream.2': 'Manage relocation while keeping community cohesion',
    'goal.downstream.3': 'Achieve sustainable safety with minimal fiscal pressure',
    'goal.team.1': 'Control flood risk while keeping resident burden stable',
    'goal.team.2': 'Balance infrastructure investment with agricultural recovery',
    'goal.team.3': 'Secure basin-wide resilience through 2100',

    // EndingPage
    'ending.tag':              '2100 — Final Evaluation',
    'ending.headline':         '{name}\'s Results',
    'ending.stats.flood':      'Cumulative Flood Damage (JPY)',
    'ending.stats.yield':      'Final Crop Yield (kg/ha)',
    'ending.stats.eco':        'Final Ecosystem Level',
    'ending.compare':          'Compare Results',
    'ending.restart':          'Play Again',
    'profile.eco.en':          'Ecosystem Steward',
    'profile.eco.label':       'Ecosystem-Focused',
    'profile.eco.desc':        'You prioritized ecosystem preservation. Trusting nature\'s resilience, you took a long-term sustainability approach.',
    'profile.engineer.en':     'Infrastructure Engineer',
    'profile.engineer.label':  'Infrastructure-Focused',
    'profile.engineer.desc':   'You managed flood risk through hard infrastructure investment. A practical engineer who trusts proven engineering solutions.',
    'profile.balanced.en':     'Adaptive Planner',
    'profile.balanced.label':  'Balanced',
    'profile.balanced.desc':   'You combined multiple policy tools for a flexible adaptation strategy. A portfolio planner preparing for an uncertain future.',
    'city.thriving.label':     'A Thriving Basin City',
    'city.thriving.text':      'By 2100, this basin has become a nationally recognized model of climate-adapted sustainable community living.',
    'city.surviving.label':    'A Town Persisting Through Change',
    'city.surviving.text':     'By 2100, the community survives despite many hardships. The handoff to the next generation continues.',
    'city.struggling.label':   'A Town Bearing the Scars',
    'city.struggling.text':    'By 2100, the marks of repeated disasters run deep, and recovery is still underway. But the people have not given up.',
    'ending.persona.title':    'Resident Persona Evaluation',
    'ending.persona.loading':  'Generating resident evaluation...',
    'ending.persona.error':    'Resident evaluation could not be generated.',
    'comparison.kicker':       'RESULT COMPARISON',
    'comparison.title':        'Compare Final Outcomes',
    'comparison.description':  'Compare your result with the no-policy baseline and saved group scores.',
    'comparison.back':         'Back',
    'comparison.loading':      'Loading comparison data...',
    'comparison.error':        'Some comparison data could not be loaded.',
    'comparison.scenario':     'Scenario',
    'comparison.yourResult':   'Your result',
    'comparison.baseline':     'Baseline: no policies',
    'comparison.flood':        'Cumulative Flood Damage',
    'comparison.yield':        'Final Crop Yield',
    'comparison.eco':          'Final Ecosystem',
    'comparison.burden':       'Avg. Resident Burden',
    'comparison.groups':       'Other Group Scores',
    'comparison.noGroups':     'No saved group score data yet.',
  },

  ja: {
    // EntryPage
    'entry.subtitle':      '2026年から2100年まで、気候変動から流域コミュニティを守る政策を選択してください。',
    'entry.username':      'ユーザー名',
    'entry.username.ph':   'あなたの名前',
    'entry.team':          'チーム名（任意）',
    'entry.team.ph':       'チーム名（任意）',
    'entry.mode.label':    '地域モード',
    'entry.upstream.name': '上流域',
    'entry.upstream.desc': '森林・堤防・田んぼダム',
    'entry.downstream.name': '下流域',
    'entry.downstream.desc': '堤防・移住・防災訓練',
    'entry.team.name':     'チーム',
    'entry.team.desc':     '上流域＋下流域・全6政策',
    'entry.rcp.label':     '気候シナリオ（RCP）',
    'entry.start':         'シミュレーション開始',
    'rcp.1.9.desc':        '強力な緩和策',
    'rcp.2.6.desc':        '中程度の緩和策',
    'rcp.4.5.desc':        '中間シナリオ',
    'rcp.6.0.desc':        '高排出',
    'rcp.8.5.desc':        '非常に高い排出',

    // TopBar
    'topbar.simple':     '🗺 概要',
    'topbar.detail':     '📊 詳細',
    'topbar.analysis':   '🔬 分析',
    'topbar.upstream':   'UPSTREAM',
    'topbar.downstream': 'DOWNSTREAM',
    'topbar.team':       'TEAM',

    // CycleReport
    'report.subtitle': 'サイクル{n} — 25年間レポート',
    'report.title':    '25年間レポートが生成されました',
    'report.flood':    '洪水被害',
    'report.crop':     '収穫量',
    'report.eco':      '生態系',
    'report.burden':   '住民負担',
    'report.cta':         '詳細を見る →',
    'report.llm_title':   'AI政策分析',
    'report.llm_loading': '分析を生成中…',

    // AnalysisPage
    'analysis.cld.title':      'システムダイナミクスモデル',
    'analysis.cld.sub':        'CAUSAL STRUCTURE',
    'analysis.scatter.title':  '政策×結果',
    'analysis.scatter.sub':    'SCATTER PLOT',
    'analysis.scatter.x':      'X軸',
    'analysis.scatter.y':      'Y軸',
    'analysis.scatter.empty':  'サイクルを実行するとデータが表示されます',

    // BasinStatus
    'basin.header':       'BASIN STATUS',
    'basin.flood.label':  '洪水リスク',
    'basin.food.label':   '食料生産',
    'basin.burden.label': '住民負担',
    'basin.eco.label':    '生態系',
    'status.low':         '低',
    'status.medium':      '中',
    'status.high':        '高',
    'status.stable':      '安定',
    'status.declining':   '低下中',
    'status.critical':    '危機',
    'status.manageable':  '許容範囲',
    'status.elevated':    '上昇中',
    'status.severe':      '深刻',
    'status.healthy':     '良好',
    'status.stressed':    'ストレス',
    'status.degraded':    '劣化',
    'budget.appliedFloodDamage': '反映洪水被害',
    'budget.pointReduction':     'ポイント減少',
    'budget.availablePoints':    '使用可能ポイント',
    'budget.floodShort':         '洪水',
    'budget.relocationShort':    '移転',
    'budget.ruleNote':           '人口減少、前25年平均洪水被害、住宅移転後のインフラ維持費に応じて、次ターンの使用可能マナが減ります。',

    // ScenarioBriefing
    'briefing.header': '⚠ シナリオ概要',
    'briefing.domains.label': '影響を受ける分野',
    'briefing.1.title': '今期、極端降水の確率が上昇',
    'briefing.1.body':  '気候モデルは今後25年サイクルで大雨の40%増加を予測しています。インフラと農業への連鎖的な影響が懸念されます。',
    'briefing.2.title': '高温ストレスによる収穫量低下が加速',
    'briefing.2.body':  '平均気温が2026年の基準値から1.2°C上昇する見込みです。適応なしでは2075年までに収穫量が持続不可能な水準に達する可能性があります。',
    'briefing.3.title': '最終局面：複合リスクがピークに',
    'briefing.3.body':  '洪水頻度・高温ストレス・人口圧力が重なります。今の政策決定がこのコミュニティの長期的な軌跡を決めます。',

    // DetailPanel
    'detail.chart.title':   '指標の推移',
    'detail.chart.sub':     'INDICATORS OVER TIME',
    'detail.llm.title':     'AI 評価',
    'detail.llm.sub':       'LLM COMMENTARY',
    'detail.llm.badge':     '接続済み',
    'detail.events.title':  'イベントログ',
    'detail.events.sub':    'EVENT LOG',
    'detail.sns.title':     '住民の反応',
    'detail.sns.sub':       'RESIDENT VOICES',
    'detail.chart.empty':   '決定を進めるとグラフが表示されます',
    'detail.llm.empty':     'サイクル終了後にAI評価が生成されます',
    'detail.llm.loading':   'AI評価を生成中…',
    'detail.llm.error':     'AI評価を生成できませんでした。',
    'detail.llm.policy':    '政策評価',
    'detail.llm.comment':   '識者コメント',
    'detail.events.empty':  'まだイベントはありません',
    'detail.sns.empty':     'サイクル終了後に住民の反応が生成されます',
    'detail.sns.loading':   '住民の反応を生成中…',
    'detail.sns.error':     '住民の反応を生成できませんでした。',
    'detail.sns.detail':    '詳細',
    'detail.sns.detail_loading': '取材中…',
    'event.flood':          '洪水被害が発生しました',
    'event.crop':           '収穫量が低下しています',
    'event.eco':            '生態系ストレスが検出されました',
    'event.none':           '今期は重大なイベントなし',
    'sns.post.1':           '今年も洪水が心配…堤防工事はいつ終わるの？早く安心して農業したい。',
    'sns.post.2':           '生態系指標が改善傾向。森林政策の効果が出始めたかも！',
    'sns.post.3':           '今期の財政報告：インフラ投資は計画通り進んでいます。引き続き注視します。',
    'sns.post.4':           'R&D投資が増えてる。将来のためにいい判断。でも今の農家さんへの支援も忘れずに',

    // LLM placeholder
    'llm.placeholder':
`【AI評価 — 第{cycle}期 ({startYear}–{endYear})】

今期の政策選択を総合的に評価します。

洪水リスクへの対応としては、堤防投資水準が妥当な範囲に維持されており、降水量増加トレンドに対して一定の防御力を確保できています。ただし、極端降水の頻度増加が続く場合、現在の堤防レベルが臨界点に達する可能性があります。

農業部門については、高温耐性R&Dへの投資が継続されているものの、効果発現までには数十年のラグがあります。中期的な収穫量低下リスクに対して追加的な措置の検討を推奨します。

生態系指標は現状維持を示していますが、持続的な改善のためには植林投資の長期的継続が不可欠です。

総合スコア：B+`,

    // DecisionPanel
    'decision.title':    '政策を選択',
    'decision.sub':      'POLICY DECISIONS',
    'decision.advance':  'Advance 25 Years ›',
    'decision.loading':  '実行中…',
    'decision.expand':   '展開',
    'decision.collapse': '収起',

    // PolicySlider tiers
    'tier.weak':     '弱',
    'tier.standard': '標準',
    'tier.strong':   '強',

    // GamePage goals
    'goal.upstream.1': '洪水リスクを抑えながら生態系を維持する',
    'goal.upstream.2': '植林拡大と財政持続性のバランスをとる',
    'goal.upstream.3': '長期的な流域強靭性を確保する',
    'goal.downstream.1': '洪水リスクへの住民曝露を低減する',
    'goal.downstream.2': 'コミュニティを維持しながら移住を管理する',
    'goal.downstream.3': '財政負担を最小化しながら持続的な安全を実現する',
    'goal.team.1': '洪水リスクを抑えながら住民負担を安定させる',
    'goal.team.2': 'インフラ投資と農業回復のバランスをとる',
    'goal.team.3': '2100年に向けた流域全体の強靭性を確保する',

    // Event pages (consequence + exogenous)
    'consequence.continue':     '続ける →',
    'event.tag.random':         'ランダムイベント',
    'event.flood.subtitle':     'RIVER FLOODING',
    'event.flood.title':        '河川氾濫',
    'event.flood.body':         '洪水被害が臨界水準を超えました。下流域の住宅地が浸水し、緊急避難が始まっています。',
    'event.drought.subtitle':   'CROP FAILURE',
    'event.drought.title':      '高温による収穫崩壊',
    'event.drought.body':       '農業R&D投資が不足したまま気温上昇が続き、今期の収穫量が持続不可能な水準を下回りました。流域全体の農家から深刻な被害報告が相次いでいます。',
    'event.wq.subtitle':        'WATER QUALITY CRISIS',
    'event.wq.title':           '河川水質悪化',
    'event.wq.body':            '森林の減少と水循環の乱れにより、河川の透明度が急落しました。アユをはじめとする清流指標生物が姿を消し、下流域の飲料水処理コストが急増しています。',
    'event.ls.subtitle':        'モデル内イベント',
    'event.ls.title':           '閾値到達',
    'event.ls.body':            'モデル内の重要な閾値に到達しました。次の政策配分では、洪水被害、食糧生産、生態系、予算負担のバランスを確認してください。',
    'event.wf.subtitle':        'モデル内イベント',
    'event.wf.title':           '閾値到達',
    'event.wf.body':            'モデル内の重要な閾値に到達しました。次の政策配分では、洪水被害、食糧生産、生態系、予算負担のバランスを確認してください。',
    'event.tb.subtitle':        'RANDOM EVENT — 技術革新',
    'event.tb.title':           '農業技術ブレークスルー',
    'event.tb.body':            '新たな耐熱性品種の開発に成功しました。高温耐性が向上し、次サイクルに向けて水資源も追加確保されました。',

    // EndingPage
    'ending.tag':              '2100年 — 最終評価',
    'ending.headline':         '{name} さんのプレイ結果',
    'ending.stats.flood':      '累計洪水被害額（円）',
    'ending.stats.yield':      '最終収穫量 (kg/ha)',
    'ending.stats.eco':        '最終生態系レベル',
    'ending.compare':          '結果を比較する',
    'ending.restart':          'もう一度プレイする',
    'profile.eco.en':          'Ecosystem Steward',
    'profile.eco.label':       '生態系重視型',
    'profile.eco.desc':        '生態系保全を優先した適応戦略を選択しました。自然の回復力を信じ、長期的な持続可能性を重視するアプローチです。',
    'profile.engineer.en':     'Infrastructure Engineer',
    'profile.engineer.label':  'インフラ重視型',
    'profile.engineer.desc':   '堤防・ダム等のハードインフラへの投資で洪水リスクを管理しました。確実性の高い工学的解決策を選ぶ実務家タイプです。',
    'profile.balanced.en':     'Adaptive Planner',
    'profile.balanced.label':  'バランス型',
    'profile.balanced.desc':   '複数の政策手段を組み合わせた柔軟な適応戦略をとりました。不確実な未来にポートフォリオで備える計画者タイプです。',
    'city.thriving.label':     '繁栄する流域都市',
    'city.thriving.text':      '2100年、この流域は気候変動に適応した持続可能なコミュニティとして、全国のモデルケースとなっています。',
    'city.surviving.label':    '変化の中で生き続ける小町',
    'city.surviving.text':     '2100年、多くの困難を乗り越えながらも、コミュニティは存続しています。次世代への引き継ぎは続く。',
    'city.struggling.label':   '苦難の痕が残る町',
    'city.struggling.text':    '2100年、繰り返す災害の痕跡は深く、復興の道はまだ続いています。しかし人々は諦めていない。',
    'ending.persona.title':    '生成AIペルソナによる評価',
    'ending.persona.loading':  '住民ペルソナの評価を生成しています...',
    'ending.persona.error':    '住民ペルソナの評価を生成できませんでした。',
    'comparison.kicker':       'RESULT COMPARISON',
    'comparison.title':        '最終結果の比較',
    'comparison.description':  'あなたの結果を、政策なしのベースラインや保存済みの他グループのスコアと比較します。',
    'comparison.back':         '戻る',
    'comparison.loading':      '比較データを読み込んでいます...',
    'comparison.error':        '一部の比較データを読み込めませんでした。',
    'comparison.scenario':     'シナリオ',
    'comparison.yourResult':   'あなたの結果',
    'comparison.baseline':     'ベースライン: 政策なし',
    'comparison.flood':        '累計洪水被害',
    'comparison.yield':        '最終収穫量',
    'comparison.eco':          '最終生態系',
    'comparison.burden':       '平均住民負担',
    'comparison.groups':       '他グループのスコア',
    'comparison.noGroups':     '保存済みの他グループスコアはまだありません。',
  },
}
