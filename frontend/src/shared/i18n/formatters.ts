import { useMemo } from "react"
import { LOCALE_TAGS, type Locale } from "./locale"
import { useLocale } from "./locale-provider"

export type Formatters = {
  readonly number: (value: number) => string
  readonly money: (value: number, currency?: string) => string
  readonly date: (value: Date | string) => string
}

export function createFormatters(locale: Locale): Formatters {
  const tag = LOCALE_TAGS[locale]
  const numbers = new Intl.NumberFormat(tag)
  const dates = new Intl.DateTimeFormat(tag, { dateStyle: "medium", timeZone: "UTC" })
  return {
    number: (value) => numbers.format(value),
    money: (value, currency = "RUB") =>
      new Intl.NumberFormat(tag, { style: "currency", currency }).format(value),
    date: (value) => dates.format(typeof value === "string" ? new Date(value) : value),
  }
}

export function useFormatters(): Formatters {
  const { locale } = useLocale()
  return useMemo(() => createFormatters(locale), [locale])
}
