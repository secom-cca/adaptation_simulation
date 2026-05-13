export const CHART_KEYS = [
  { key: 'Flood Damage JPY', labelEn: 'Flood Damage (JPY)', labelJa: '洪水被害（円）', color: '#3d6b8f' },
  { key: 'Crop Yield', labelEn: 'Crop Yield (kg/ha)', labelJa: '食糧生産（kg/ha）', color: '#4a8c5c' },
  { key: 'Ecosystem Level', labelEn: 'Ecosystem Level', labelJa: '生態系指標', color: '#5a7c3d' },
  { key: 'Resident Burden', labelEn: 'Resident / Budget Burden', labelJa: '住民・予算負担', color: '#8c5a3d' },
  { key: 'Municipal Cost', labelEn: 'Policy Cost', labelJa: '政策費用', color: '#7a5a8c' },
  { key: 'Temperature (°C)', labelEn: 'Temperature (°C)', labelJa: '気温（℃）', color: '#e07a3a' },
  { key: 'Precipitation (mm)', labelEn: 'Precipitation (mm)', labelJa: '年降水量（mm）', color: '#5a8caf' },
  { key: 'Extreme Precip Frequency', labelEn: 'Extreme Precip Freq', labelJa: '極端降雨頻度', color: '#7a5aaf' },
  { key: 'available_water', labelEn: 'Available Water (mm)', labelJa: '利用可能水量（mm）', color: '#5a8c8c' },
  { key: 'Forest Area', labelEn: 'Forest Area (ha)', labelJa: '森林面積（ha）', color: '#3d7a4a' },
  { key: 'Levee Level', labelEn: 'Levee Level', labelJa: '堤防水準', color: '#6a7a8c' },
  { key: 'Resident capacity', labelEn: 'Resident Capacity', labelJa: '住民防災能力', color: '#8c7a3d' },
  { key: 'risky_house_total', labelEn: 'High-Risk Households', labelJa: '高リスク住宅数', color: '#8c3d3d' },
  { key: 'paddy_dam_area', labelEn: 'Paddy Dam Area (ha)', labelJa: '田んぼダム導入面積', color: '#6a8c5a' },
]

export function fmtY(v) {
  if (typeof v !== 'number') return v
  const abs = Math.abs(v)
  if (abs >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}億`
  if (abs >= 10_000) return `${(v / 10_000).toFixed(0)}万`
  if (abs >= 1_000) return `${(v / 1_000).toFixed(1)}K`
  return v.toFixed(1)
}
