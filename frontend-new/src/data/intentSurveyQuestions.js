/** Short intent survey shown right after 「25年進める」 (~30 sec). */

export const INTENT_SURVEY_VERSION = 2

export const INTENT_OBJECTIVE_OPTIONS = [
  {
    value: 'flood_score',
    label: {
      ja: '洪水被害スコアを上げたい（被害を減らしたい）',
      en: 'Improve the flood-damage score (reduce damage)',
    },
  },
  {
    value: 'crop_score',
    label: {
      ja: '農作物生産スコアを上げたい',
      en: 'Improve the crop-production score',
    },
  },
  {
    value: 'ecosystem_score',
    label: {
      ja: '生態系スコアを上げたい',
      en: 'Improve the ecosystem score',
    },
  },
  {
    value: 'unsure',
    label: {
      ja: '特に決めていない／わからない',
      en: 'Not sure / no particular goal',
    },
  },
]

export function emptyIntentSurveyAnswers() {
  return {
    target_objectives: [],
    free_text: '',
  }
}

export function isIntentSurveyComplete(answers = {}) {
  return Array.isArray(answers.target_objectives) && answers.target_objectives.length > 0
}

export function buildIntentSurveyPayload({
  answers,
  cycle,
  year,
  sliders = null,
} = {}) {
  return {
    version: INTENT_SURVEY_VERSION,
    submitted_at: new Date().toISOString(),
    cycle,
    year_range: {
      start_year: year,
      end_year: year + 24,
    },
    answers: {
      target_objectives: [...(answers?.target_objectives || [])],
      free_text: String(answers?.free_text || '').trim(),
    },
    sliders: sliders ? { ...sliders } : null,
  }
}
