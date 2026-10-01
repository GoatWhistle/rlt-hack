export const LOCALES = ["ru", "en"] as const

export type Locale = (typeof LOCALES)[number]

export const DEFAULT_LOCALE: Locale = "ru"

export const LOCALE_STORAGE_KEY = "rlt-locale"

export const LOCALE_TAGS: Record<Locale, string> = {
  ru: "ru-RU",
  en: "en-US",
}

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value)
}

export function toLocale(language: string | null | undefined): Locale | null {
  const base = language?.split("-")[0]?.toLowerCase()
  return isLocale(base) ? base : null
}

export function readStoredLocale(): Locale | null {
  try {
    return toLocale(localStorage.getItem(LOCALE_STORAGE_KEY))
  } catch {
    return null
  }
}

export function writeStoredLocale(locale: Locale): void {
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  } catch {
    return
  }
}

export function navigatorLocale(): Locale | null {
  if (typeof navigator === "undefined") return null
  const languages = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const language of languages) {
    const locale = toLocale(language)
    if (locale) return locale
  }
  return null
}

export function resolveLocale(): Locale {
  return readStoredLocale() ?? navigatorLocale() ?? DEFAULT_LOCALE
}
