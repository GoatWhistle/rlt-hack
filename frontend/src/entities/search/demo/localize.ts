import { LOCALES, type Locale } from "@/shared/i18n/locale"

export type Loose = Readonly<Record<string, unknown>>

const LOCALIZED_KEYS = [...LOCALES].sort().join()

function isRecord(value: unknown): value is Loose {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isLocalized(value: Loose): value is Readonly<Record<Locale, unknown>> {
  return Object.keys(value).sort().join() === LOCALIZED_KEYS
}

export function localize(value: unknown, locale: Locale): unknown {
  if (Array.isArray(value)) return value.map((entry) => localize(entry, locale))
  if (!isRecord(value)) return value
  if (isLocalized(value)) return value[locale]
  return Object.fromEntries(
    Object.entries(value).map(([key, entry]) => [key, localize(entry, locale)]),
  )
}

export function omit(value: unknown, keys: readonly string[]): Loose {
  if (!isRecord(value)) return {}
  return Object.fromEntries(Object.entries(value).filter(([key]) => !keys.includes(key)))
}

export function records(value: unknown): Loose[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}
