/** 金额：分请直接传元数值，统一保留两位 */
export function money(n: number | string | undefined | null): string {
  const v = Number(n ?? 0)
  return v.toFixed(2)
}

export function datetime(value: string | Date | undefined | null): string {
  if (!value) return ''
  const d = typeof value === 'string' ? new Date(value.replace(/-/g, '/')) : value
  if (Number.isNaN(d.getTime())) return String(value)
  const pad = (x: number) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
