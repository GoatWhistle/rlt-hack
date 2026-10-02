import { LOCALE_TAGS, type Locale } from "./locale"
import { useLocale } from "./locale-provider"

export type Formatters = {
  readonly number: (value: number) => string
  readonly percent: (value: number) => string
  readonly money: (value: number, currency?: string) => string
  readonly price: (value: number) => string
  readonly date: (value: Date | string) => string
  readonly dateTime: (value: Date | string) => string
  readonly time: (value: Date | string) => string
  readonly list: (items: readonly string[]) => string
  readonly relative: (value: number, unit: Intl.RelativeTimeFormatUnit) => string
}

const cache = new Map<Locale, Formatters>()

function toDate(value: Date | string): Date {
  return typeof value === "string" ? new Date(value) : value
}

function build(locale: Locale): Formatters {
  const tag = LOCALE_TAGS[locale]
  const numbers = new Intl.NumberFormat(tag)
  const percents = new Intl.NumberFormat(tag, { style: "percent", maximumFractionDigits: 0 })
  const currencies = new Map<string, Intl.NumberFormat>()
  const dates = new Intl.DateTimeFormat(tag, { dateStyle: "medium", timeZone: "UTC" })
  const dateTimes = new Intl.DateTimeFormat(tag, { dateStyle: "medium", timeStyle: "short" })
  const times = new Intl.DateTimeFormat(tag, { timeStyle: "short" })
  const lists = new Intl.ListFormat(tag, { type: "conjunction" })
  const relatives = new Intl.RelativeTimeFormat(tag, { numeric: "auto" })
  const prices = new Intl.NumberFormat(tag, {
    style: "currency",
    currency: "RUB",
    currencyDisplay: "narrowSymbol",
    trailingZeroDisplay: "stripIfInteger",
  })
  const currencyFormat = (currency: string) => {
    const known = currencies.get(currency)
    if (known) return known
    const created = new Intl.NumberFormat(tag, {
      style: "currency",
      currency,
      currencyDisplay: "narrowSymbol",
    })
    currencies.set(currency, created)
    return created
  }
  return {
    number: (value) => numbers.format(value),
    percent: (value) => percents.format(value),
    money: (value, currency = "RUB") => currencyFormat(currency).format(value),
    price: (value) => prices.format(value),
    date: (value) => dates.format(toDate(value)),
    dateTime: (value) => dateTimes.format(toDate(value)),
    time: (value) => times.format(toDate(value)),
    list: (items) => lists.format(items),
    relative: (value, unit) => {
      const phrase = relatives.format(value, unit)
      return phrase.charAt(0).toLocaleUpperCase(tag) + phrase.slice(1)
    },
  }
}

export function createFormatters(locale: Locale): Formatters {
  const known = cache.get(locale)
  if (known) return known
  const created = build(locale)
  cache.set(locale, created)
  return created
}

export function useFormatters(): Formatters {
  const { locale } = useLocale()
  return createFormatters(locale)
}
