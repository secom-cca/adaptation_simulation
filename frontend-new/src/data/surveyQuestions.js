/** Post-play survey (~3 min). */

export const SURVEY_VERSION = 7

/**
 * Question keys become answers object keys.
 * research_tags document which research question each item supports.
 */
export const SURVEY_QUESTIONS = [
  {
    id: 'age_decade',
    type: 'single',
    required: true,
    research_tags: ['participant'],
    label: {
      ja: 'あなたの年代を教えてください',
      en: 'Which age group are you in?',
    },
    options: [
      { value: '10s', label: { ja: '10代', en: 'Teens' } },
      { value: '20s', label: { ja: '20代', en: '20s' } },
      { value: '30s', label: { ja: '30代', en: '30s' } },
      { value: '40s', label: { ja: '40代', en: '40s' } },
      { value: '50s', label: { ja: '50代', en: '50s' } },
      { value: '60s_plus', label: { ja: '60代以上', en: '60+' } },
      { value: 'prefer_not', label: { ja: '答えたくない', en: 'Prefer not to say' } },
    ],
  },
  {
    id: 'prior_climate_adaptation_knowledge',
    type: 'likert5',
    required: true,
    research_tags: ['participant', 'learning'],
    label: {
      ja: 'この体験の前から、「気候変動適応」について知っていましたか？',
      en: 'Before this experience, how familiar were you with climate adaptation?',
    },
    likertLabels: {
      ja: { low: 'まったく知らなかった', high: 'よく知っていた' },
      en: { low: 'Not at all', high: 'Very familiar' },
    },
  },
  {
    id: 'prior_basin_flood_management_knowledge',
    type: 'likert5',
    required: true,
    research_tags: ['participant', 'learning'],
    label: {
      ja: 'この体験の前から、「流域治水」について知っていましたか？',
      en: 'Before this experience, how familiar were you with basin-based flood management?',
    },
    likertLabels: {
      ja: { low: 'まったく知らなかった', high: 'よく知っていた' },
      en: { low: 'Not at all', high: 'Very familiar' },
    },
  },
  {
    id: 'adaptation_can_reduce_disaster',
    type: 'likert5',
    required: true,
    research_tags: ['efficacy', 'learning'],
    label: {
      ja: '自治体の気候変動適応策によって、防災はできそうだと感じましたか？',
      en: 'Did you feel that municipal climate adaptation measures could help with disaster prevention?',
    },
    likertLabels: {
      ja: { low: 'まったくそう思わない', high: '強くそう思う' },
      en: { low: 'Strongly disagree', high: 'Strongly agree' },
    },
  },
  {
    id: 'understood_policy_effects',
    type: 'likert5',
    required: true,
    research_tags: ['efficacy', 'learning'],
    label: {
      ja: '施策を適切に実施することで、よい将来が実現できると思いましたか？',
      en: 'Did you feel that appropriately implementing measures could lead to a better future?',
    },
    likertLabels: {
      ja: { low: 'まったくそう思わない', high: '強くそう思う' },
      en: { low: 'Strongly disagree', high: 'Strongly agree' },
    },
  },
  {
    id: 'what_learned',
    type: 'multi',
    required: true,
    research_tags: ['learning'],
    label: {
      ja: 'この体験で学んだことは何ですか？（複数選択可）',
      en: 'What did you learn from this experience? (Select all that apply)',
    },
    options: [
      {
        value: 'climate_impacts',
        label: {
          ja: '気候変動による様々な影響（洪水，農業など）',
          en: 'Various impacts of climate change (floods, agriculture, etc.)',
        },
      },
      {
        value: 'climate_uncertainty',
        label: {
          ja: '気候変動による将来の不確実性',
          en: 'Future uncertainty due to climate change',
        },
      },
      {
        value: 'basin_flood_measures',
        label: {
          ja: '様々な流域治水対策（住宅移転，田んぼダムなど）',
          en: 'Various basin-based flood measures (relocation, paddy dams, etc.)',
        },
      },
      {
        value: 'time_to_effect',
        label: {
          ja: '効果がかかるまでの時間への留意（森林保全，など）',
          en: 'Attention to time lags before effects appear (e.g. forest conservation)',
        },
      },
      {
        value: 'multi_goal_balance',
        label: {
          ja: '複数の目標のバランスを取ることの難しさ（治水と農業，生態系など）',
          en: 'Difficulty of balancing multiple goals (flood control, agriculture, ecosystems, etc.)',
        },
      },
      {
        value: 'budget_decision',
        label: {
          ja: '予算や制約のもとでの意思決定の難しさ',
          en: 'Difficulty of decision-making under budget and other constraints',
        },
      },
    ],
  },
  {
    id: 'priority_indicators',
    type: 'multi',
    required: true,
    research_tags: ['priorities', 'objectives'],
    label: {
      ja: 'どの指標を重要視していましたか？（複数選択可）',
      en: 'Which indicators did you prioritize? (Select all that apply)',
    },
    options: [
      {
        value: 'flood_score',
        label: {
          ja: '洪水被害スコア（被害を減らすこと）',
          en: 'Flood-damage score (reducing damage)',
        },
      },
      {
        value: 'crop_score',
        label: { ja: '農作物生産スコア', en: 'Crop-production score' },
      },
      {
        value: 'ecosystem_score',
        label: { ja: '生態系スコア', en: 'Ecosystem score' },
      },
      {
        value: 'unsure',
        label: { ja: '特に決めていない／わからない', en: 'Not sure / no particular priority' },
      },
    ],
  },
  {
    id: 'learning_free_text',
    type: 'text',
    required: false,
    research_tags: ['learning'],
    label: {
      ja: '学んだことや気づきがあれば、書いてください（任意）',
      en: 'If you learned anything or noticed something, please write it here (optional)',
    },
    maxLength: 500,
  },
  {
    id: 'game_impression',
    type: 'text',
    required: false,
    research_tags: ['feedback'],
    label: {
      ja: 'このゲームに対する感想（任意）',
      en: 'Your impressions of this game (optional)',
    },
    maxLength: 500,
  },
  {
    id: 'other_comments',
    type: 'text',
    required: false,
    research_tags: ['feedback'],
    label: {
      ja: 'その他・何かあれば（任意）',
      en: 'Anything else you would like to add (optional)',
    },
    maxLength: 500,
  },
]

export function emptySurveyAnswers() {
  const answers = {}
  for (const q of SURVEY_QUESTIONS) {
    if (q.type === 'multi') answers[q.id] = []
    else if (q.type === 'text') answers[q.id] = ''
    else answers[q.id] = null
  }
  return answers
}

export function isSurveyComplete(answers = {}) {
  return SURVEY_QUESTIONS.every(q => {
    if (!q.required) return true
    const v = answers[q.id]
    if (q.type === 'multi') return Array.isArray(v) && v.length > 0
    if (q.type === 'text') return true
    return v !== null && v !== undefined && v !== ''
  })
}

export function buildSurveyPayload(answers) {
  return {
    version: SURVEY_VERSION,
    submitted_at: new Date().toISOString(),
    answers: { ...answers },
    research_focus: [
      'prior_climate_adaptation_knowledge',
      'prior_basin_flood_management_knowledge',
      'municipal_adaptation_and_disaster_prevention',
      'understood_policy_effects',
      'what_participants_learned',
      'priority_indicators',
      'open_feedback',
    ],
  }
}
