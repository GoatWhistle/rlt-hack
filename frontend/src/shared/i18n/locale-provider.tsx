import type { ReactNode } from "react"
import { createContext, use, useCallback, useEffect, useMemo, useState } from "react"
import { I18nextProvider } from "react-i18next"
import { i18n, initI18n } from "./i18n"
import { type Locale, resolveLocale, writeStoredLocale } from "./locale"

export type LocaleContextValue = {
  readonly locale: Locale
  readonly setLocale: (locale: Locale) => void
}

const LocaleContext = createContext<LocaleContextValue | null>(null)

export type LocaleProviderProps = {
  readonly children: ReactNode
  readonly initialLocale?: Locale
}

export function LocaleProvider({ children, initialLocale }: LocaleProviderProps) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const start = initialLocale ?? resolveLocale()
    initI18n(start)
    return start
  })

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    writeStoredLocale(next)
  }, [])

  useEffect(() => {
    document.documentElement.lang = locale
    if (i18n.language !== locale) void i18n.changeLanguage(locale)
  }, [locale])

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale])

  return (
    <I18nextProvider i18n={i18n}>
      <LocaleContext value={value}>{children}</LocaleContext>
    </I18nextProvider>
  )
}

export function useLocale(): LocaleContextValue {
  const value = use(LocaleContext)
  if (!value) throw new Error("useLocale must be used within LocaleProvider")
  return value
}
