export function formatJpyInline(value) {
  const num = Number(value)

  if (!Number.isFinite(num)) return '—'

  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''

  if (abs >= 100_000_000) {
    return `${sign}${(abs / 100_000_000).toFixed(1).replace(/\.0$/, '')}億円`
  }

  if (abs >= 10_000) {
    return `${sign}${(abs / 10_000).toFixed(1).replace(/\.0$/, '')}万円`
  }

  return `${sign}${Math.round(abs).toLocaleString('ja-JP')}円`
}

export function formatJpyShort(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `${(amount / 100_000_000).toFixed(1)}億円`
  if (amount >= 10_000) return `${Math.round(amount / 10_000).toLocaleString()}万円`
  return `${Math.round(amount).toLocaleString()}円`
}

export function formatJpy(value) {
  const amount = Number(value) || 0
  if (amount >= 100_000_000) return `被害額 約${(amount / 100_000_000).toFixed(1)}億円。`
  if (amount >= 10_000) return `被害額 約${Math.round(amount / 10_000).toLocaleString()}万円。`
  return `被害額 約${Math.round(amount).toLocaleString()}円。`
}

export default { formatJpyInline, formatJpyShort, formatJpy }
