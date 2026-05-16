import generatedBenchmarkSeries from './benchmark_series.json'
import generatedScoreBounds from './score_bounds.json'

export const TARGET_YEARS = [2050, 2075, 2100]

export const TARGET_YEAR_PERIODS = {
  2050: { start: 2026, end: 2050 },
  2075: { start: 2051, end: 2075 },
  2100: { start: 2076, end: 2100 },
}

/**
 * 表示用スコア基準。
 *
 * 意図：
 * - 洪水被害：温暖化で後半ほど被害規模が大きくなるため、2050/2075/2100で別基準
 * - 農作物生産高：全期間で同じ基準
 * - 生態系：全期間で同じ基準
 * - baseline は 2050 → 2075 → 2100 でだんだん悪化
 * - AI最適解は悪化を完全には止めないが、踏みとどまる
 */
export const FALLBACK_SCORE_BOUNDS = {
  flood: {
    2050: {
      good: 400_000_000,
      bad: 900_000_000,
    },
    2075: {
      good: 800_000_000,
      bad: 1_800_000_000,
    },
    2100: {
      good: 1_200_000_000,
      bad: 2_700_000_000,
    },
  },
  crop: {
    bad: 3200,
    good: 5000,
  },
  ecosystem: {
    bad: 67.5,
    good: 80.0,
  },
}

export const FALLBACK_BENCHMARK_SERIES = {
  baseline: {
    labelJa: 'ベースライン（対策なし）',
    labelEn: 'Baseline',
    years: {
      2050: {
        floodDamageJpy: 225_133_701,
        cropYield: 4860.2,
        ecosystemLevel: 73.89,
      },
      2075: {
        floodDamageJpy: 761_025_577,
        cropYield: 4493.4,
        ecosystemLevel: 71.43,
      },
      2100: {
        floodDamageJpy: 2_269_047_448,
        cropYield: 3692.7,
        ecosystemLevel: 69.41,
      },
    },
  },
  aiOptimal: {
    labelJa: 'AIエージェント最適解',
    labelEn: 'AI optimal',
    policiesJa: [
      'T1: 植林5 / 田んぼダム2 / 防災訓練1 / 農業R&D2',
      'T2: 植林1 / 田んぼダム4 / 農業R&D3',
      'T3: 植林1 / 田んぼダム2 / 農業R&D3',
    ],
    years: {
      2050: {
        floodDamageJpy: 199_292_489,
        cropYield: 4889.9,
        ecosystemLevel: 73.89,
      },
      2075: {
        floodDamageJpy: 588_338_898,
        cropYield: 4693.3,
        ecosystemLevel: 72.21,
      },
      2100: {
        floodDamageJpy: 1_844_485_118,
        cropYield: 4159.8,
        ecosystemLevel: 71.52,
      },
    },
  },
}

export const SCORE_BOUNDS = generatedScoreBounds ?? FALLBACK_SCORE_BOUNDS
export const BENCHMARK_SERIES = generatedBenchmarkSeries ?? FALLBACK_BENCHMARK_SERIES

export function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Number(value) || 0))
}

export function floodJpy(row = {}) {
  return Number(row['Flood Damage JPY'] ?? ((row['Flood Damage'] ?? 0) * 150)) || 0
}

export function nearestRow(rows = [], targetYear) {
  if (!rows.length) return {}

  return rows.reduce((best, row) => {
    const bestGap = Math.abs((best.year ?? best.Year ?? 0) - targetYear)
    const rowGap = Math.abs((row.year ?? row.Year ?? 0) - targetYear)
    return rowGap < bestGap ? row : best
  }, rows[0])
}

function yearOf(row = {}) {
  return Number(row.year ?? row.Year ?? 0) || 0
}

function rowsInPeriod(rows = [], targetYear) {
  const period = TARGET_YEAR_PERIODS[targetYear]

  if (!period) {
    const row = nearestRow(rows, targetYear)
    return row ? [row] : []
  }

  return rows.filter(row => {
    const year = yearOf(row)
    return year >= period.start && year <= period.end
  })
}

function averageMetric(rows = [], key, fallbackValue = 0) {
  const values = rows
    .map(row => Number(row[key]))
    .filter(value => Number.isFinite(value))

  if (!values.length) return fallbackValue

  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function cumulativeFloodDamageJpy(rows = [], fallbackValue = 0) {
  const values = rows
    .map(row => floodJpy(row))
    .filter(value => Number.isFinite(value))

  if (!values.length) return fallbackValue

  return values.reduce((sum, value) => sum + value, 0)
}

function averagedRowForTargetYear(rows = [], targetYear) {
  const nearest = nearestRow(rows, targetYear)
  const periodRows = rowsInPeriod(rows, targetYear)

  const floodDamageCumulative = cumulativeFloodDamageJpy(
    periodRows,
    floodJpy(nearest),
  )

  return {
    ...nearest,
    year: targetYear,
    Year: targetYear,

    // 洪水被害は当該25年間の累計
    'Flood Damage JPY': floodDamageCumulative,

    // Flood Damage は JPY が主に使われるので、換算値として保持
    'Flood Damage': floodDamageCumulative / 150,

    // 農作物生産高・生態系は当該25年間の平均
    'Crop Yield': averageMetric(
      periodRows,
      'Crop Yield',
      Number(nearest?.['Crop Yield']) || 0,
    ),
    'Ecosystem Level': averageMetric(
      periodRows,
      'Ecosystem Level',
      Number(nearest?.['Ecosystem Level']) || 0,
    ),
  }
}

function highGoodScore(value, badValue, goodValue) {
  return clamp(
    ((Number(value) - Number(badValue)) / Math.max(Number(goodValue) - Number(badValue), 1e-9)) * 100,
  )
}

function lowGoodScore(value, goodValue, badValue) {
  return clamp(
    ((Number(badValue) - Number(value)) / Math.max(Number(badValue) - Number(goodValue), 1e-9)) * 100,
  )
}

export function scoresForRow(row = {}, targetYear = 2100) {
  const floodValue = floodJpy(row)
  const cropValue = Number(row['Crop Yield']) || 0
  const ecosystemValue = Number(row['Ecosystem Level']) || 0

  const floodBounds = SCORE_BOUNDS.flood[targetYear] ?? SCORE_BOUNDS.flood[2100]

  const floodScore = lowGoodScore(
    floodValue,
    floodBounds.good,
    floodBounds.bad,
  )

  const cropScore = highGoodScore(
    cropValue,
    SCORE_BOUNDS.crop.bad,
    SCORE_BOUNDS.crop.good,
  )

  const ecosystemScore = highGoodScore(
    ecosystemValue,
    SCORE_BOUNDS.ecosystem.bad,
    SCORE_BOUNDS.ecosystem.good,
  )

  const totalScore = (floodScore + cropScore + ecosystemScore) / 3

  return {
    floodScore,
    cropScore,
    ecosystemScore,
    totalScore,
  }
}

export function buildYearSnapshots(rows = []) {
  return TARGET_YEARS.map(year => {
    const row = averagedRowForTargetYear(rows, year)

    return {
      year,
      row,
      scores: scoresForRow(row, year),
      metrics: {
        floodDamageJpy: floodJpy(row),
        cropYield: Number(row['Crop Yield']) || 0,
        ecosystemLevel: Number(row['Ecosystem Level']) || 0,
      },
    }
  })
}

export function finalScores(rows = []) {
  const snapshots = buildYearSnapshots(rows)
  if (!snapshots.length) return scoresForRow({}, 2100)
  return averageScores(snapshots.map(snapshot => snapshot.scores))
}

export function benchmarkSnapshots(key) {
  const benchmark = BENCHMARK_SERIES[key]
  if (!benchmark) return []

  return TARGET_YEARS.map(year => {
    const metrics = benchmark.years[year] ?? benchmark.years[String(year)] ?? {}

    const row = {
      year,
      'Flood Damage JPY': metrics.floodDamageJpy ?? 0,
      'Crop Yield': metrics.cropYield ?? 0,
      'Ecosystem Level': metrics.ecosystemLevel ?? 0,
    }

    return {
      year,
      row,
      metrics,
      scores: scoresForRow(row, year),
    }
  })
}

export function benchmarkSummary(key) {
  return averageScores(benchmarkSnapshots(key).map(snapshot => snapshot.scores))
}

function averageScores(scoresList = []) {
  const count = scoresList.length || 1

  const sum = scoresList.reduce((acc, scores) => ({
    floodScore: acc.floodScore + (scores.floodScore || 0),
    cropScore: acc.cropScore + (scores.cropScore || 0),
    ecosystemScore: acc.ecosystemScore + (scores.ecosystemScore || 0),
    totalScore: acc.totalScore + (scores.totalScore || 0),
  }), {
    floodScore: 0,
    cropScore: 0,
    ecosystemScore: 0,
    totalScore: 0,
  })

  return {
    floodScore: sum.floodScore / count,
    cropScore: sum.cropScore / count,
    ecosystemScore: sum.ecosystemScore / count,
    totalScore: sum.totalScore / count,
  }
}

export function round1(value) {
  return Math.round((Number(value) || 0) * 10) / 10
}
