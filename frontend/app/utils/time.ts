const DAY_NAMES = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
const MONTH_NAMES = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

function toDate(iso: string): Date {
  return new Date(iso)
}

function isToday(d: Date): boolean {
  const now = new Date()
  return d.getDate() === now.getDate() && d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
}

function isYesterday(d: Date): boolean {
  const y = new Date()
  y.setDate(y.getDate() - 1)
  return d.getDate() === y.getDate() && d.getMonth() === y.getMonth() && d.getFullYear() === y.getFullYear()
}

function isThisWeek(d: Date): boolean {
  const now = new Date()
  const weekAgo = new Date(now.getTime() - 6 * 86400000)
  return d >= weekAgo && d <= now
}

function isThisYear(d: Date): boolean {
  return d.getFullYear() === new Date().getFullYear()
}

function pad2(n: number): string {
  return n.toString().padStart(2, '0')
}

/** Time only: "14:05" */
export function formatTime(iso: string): string {
  const d = toDate(iso)
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

/** Relative date for session list sidebar */
export function formatRelativeDate(iso: string): string {
  if (!iso) return ''
  const d = toDate(iso)
  if (isToday(d)) return formatTime(iso)
  if (isYesterday(d)) return 'вчера'
  if (isThisWeek(d)) return DAY_NAMES[d.getDay()]
  if (isThisYear(d)) return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]}`
  return `${pad2(d.getDate())}.${pad2(d.getMonth() + 1)}.${d.getFullYear()}`
}

/** Day header for chat grouping (like Telegram) */
export function formatDayHeader(iso: string): string {
  if (!iso) return ''
  const d = toDate(iso)
  if (isToday(d)) return 'Сегодня'
  if (isYesterday(d)) return 'Вчера'
  if (isThisWeek(d)) return DAY_NAMES[d.getDay()].charAt(0).toUpperCase() + DAY_NAMES[d.getDay()].slice(1)
  if (isThisYear(d)) return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]}`
  return `${d.getDate()} ${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`
}

/** Check if two ISO dates are on different days */
export function isDifferentDay(a: string, b: string): boolean {
  if (!a || !b) return true
  const da = toDate(a), db = toDate(b)
  return da.getDate() !== db.getDate() || da.getMonth() !== db.getMonth() || da.getFullYear() !== db.getFullYear()
}
