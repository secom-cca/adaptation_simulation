export const CHART_KEYS = [
  // outcomes
  { key: 'Flood Damage',             labelEn: 'Flood Damage (USD)',      labelJa: '洪水被害 (USD)',         color: '#3d6b8f' },
  { key: 'Crop Yield',               labelEn: 'Crop Yield (kg/ha)',      labelJa: '収穫量 (kg/ha)',         color: '#4a8c5c' },
  { key: 'Ecosystem Level',          labelEn: 'Ecosystem Level',         labelJa: '生態系レベル',           color: '#5a7c3d' },
  { key: 'Resident Burden',          labelEn: 'Resident Burden',         labelJa: '住民負担',               color: '#8c5a3d' },
  { key: 'Municipal Cost',           labelEn: 'Municipal Cost (USD)',     labelJa: '財政コスト (USD)',       color: '#7a5a8c' },
  // climate
  { key: 'Temperature (℃)',          labelEn: 'Temperature (°C)',        labelJa: '気温 (°C)',              color: '#e07a3a' },
  { key: 'Precipitation (mm)',        labelEn: 'Precipitation (mm)',      labelJa: '年降水量 (mm)',          color: '#5a8caf' },
  { key: 'Extreme Precip Frequency', labelEn: 'Extreme Precip Freq',     labelJa: '極端降水頻度',           color: '#7a5aaf' },
  // intermediate
  { key: 'available_water',          labelEn: 'Available Water (mm)',    labelJa: '利用可能水量 (mm)',      color: '#5a8c8c' },
  { key: 'Forest Area',              labelEn: 'Forest Area (ha)',        labelJa: '森林面積 (ha)',          color: '#3d7a4a' },
  { key: 'Levee Level',              labelEn: 'Levee Level',             labelJa: '堤防レベル',             color: '#6a7a8c' },
  { key: 'Resident capacity',        labelEn: 'Resident Capacity',       labelJa: '住民防災能力',           color: '#8c7a3d' },
  { key: 'risky_house_total',        labelEn: 'High-Risk Households',    labelJa: '高リスク住宅数',         color: '#8c3d3d' },
  { key: 'paddy_dam_area',           labelEn: 'Paddy Dam Area (ha)',     labelJa: '田んぼダム面積 (ha)',    color: '#6a8c5a' },
]

export function fmtY(v) {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000)     return `${(v / 1_000).toFixed(1)}K`
  return typeof v === 'number'  ? v.toFixed(1) : v
}
