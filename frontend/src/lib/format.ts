// Las fechas de la API vienen como "AAAA-MM-DD" (sin zona): se arman en hora local para no correrlas un día.
export function parseDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)
  return new Date(year, month - 1, day)
}

const weekdayFormat = new Intl.DateTimeFormat('es-UY', { weekday: 'short' })
const monthFormat = new Intl.DateTimeFormat('es-UY', { month: 'long', year: 'numeric' })
const shortFormat = new Intl.DateTimeFormat('es-UY', { day: 'numeric', month: 'short' })
const longFormat = new Intl.DateTimeFormat('es-UY', { weekday: 'long', day: 'numeric', month: 'long' })

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

export const weekdayShort = (iso: string) => capitalize(weekdayFormat.format(parseDate(iso)).replace('.', ''))
export const monthLabel = (iso: string) => capitalize(monthFormat.format(parseDate(iso)))
export const dateShort = (iso: string) => shortFormat.format(parseDate(iso)).replace('.', '')
export const dateLong = (iso: string) => capitalize(longFormat.format(parseDate(iso)))
export const dayNumber = (iso: string) => String(parseDate(iso).getDate())
export const timeShort = (isoTime: string) => isoTime.slice(0, 5)

export const formatAverage = (value: number | null) =>
  value === null ? '–' : value.toLocaleString('es-UY', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export function groupByMonth<T extends { date: string }>(items: T[]): { month: string; items: T[] }[] {
  const groups: { month: string; items: T[] }[] = []
  for (const item of items) {
    const month = monthLabel(item.date)
    const last = groups.at(-1)
    if (last?.month === month) last.items.push(item)
    else groups.push({ month, items: [item] })
  }
  return groups
}

export const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`
