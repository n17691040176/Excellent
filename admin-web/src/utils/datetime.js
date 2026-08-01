import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

export const BUSINESS_TIMEZONE = 'Asia/Shanghai'

const OFFSET_SUFFIX_RE = /(?:Z|[+-]\d{2}:?\d{2})$/i
const SERVER_DATETIME_RE = /^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?$/

function normalizeServerDateTime(value) {
  if (typeof value !== 'string') return value
  const text = value.trim()
  if (SERVER_DATETIME_RE.test(text) && !OFFSET_SUFFIX_RE.test(text)) return `${text.replace(' ', 'T')}Z`
  return text
}

export function parseServerDateTime(value) {
  if (!value) return null
  const parsed = dayjs(normalizeServerDateTime(value))
  return parsed.isValid() ? parsed.tz(BUSINESS_TIMEZONE) : null
}

export function formatDateTime(value, fallback = '--') {
  return parseServerDateTime(value)?.format('YYYY-MM-DD HH:mm') || fallback
}

export function formatDateTimeInput(value) {
  return parseServerDateTime(value)?.format('YYYY-MM-DDTHH:mm:ss') || null
}

export function serverDateTimeToDate(value) {
  const parsed = parseServerDateTime(value)
  if (!parsed) return null
  return new Date(
    parsed.year(),
    parsed.month(),
    parsed.date(),
    parsed.hour(),
    parsed.minute(),
    parsed.second(),
    parsed.millisecond()
  )
}

export function shanghaiDateTimeToUtcISOString(value) {
  if (!value) return null
  if (value instanceof Date) {
    const wallTime = dayjs(value).format('YYYY-MM-DDTHH:mm:ss.SSS')
    return dayjs.tz(wallTime, BUSINESS_TIMEZONE).utc().toISOString()
  }
  const text = String(value).trim()
  const parsed = OFFSET_SUFFIX_RE.test(text) ? dayjs(text) : dayjs.tz(text, BUSINESS_TIMEZONE)
  return parsed.isValid() ? parsed.utc().toISOString() : null
}

export function isDateTimeInShanghaiDateRange(value, startDate, endDate) {
  const parsed = parseServerDateTime(value)
  if (!parsed) return false
  const start = dayjs.tz(`${startDate} 00:00:00`, BUSINESS_TIMEZONE)
  const end = dayjs.tz(`${endDate} 23:59:59.999`, BUSINESS_TIMEZONE)
  return !parsed.isBefore(start) && !parsed.isAfter(end)
}
