import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import {
  isRegionCode,
  MAJOR_CITY_CODES,
  REGION_CODES,
  type RegionCode,
} from "@/entities/evidence/regions"
import {
  DEFAULT_LOCALE,
  LOCALE_TAGS,
  LOCALES,
  type Locale,
  toLocale,
} from "@/shared/i18n/locale"
import type { ComboboxGroup, ComboboxOption } from "@/shared/ui/combobox"

type Dictionary = Readonly<Partial<Record<string, string>>>

export type RegionNames = {
  readonly region: Dictionary
  readonly city: Dictionary
  readonly alias: Dictionary
}

export function splitAliases(text: string | undefined): string[] {
  return (text ?? "")
    .split(",")
    .map((word) => word.trim())
    .filter((word) => word !== "")
}

type Bundle = Readonly<Partial<Record<keyof RegionNames | string, unknown>>>

function dictionary(value: unknown): Dictionary {
  return value && typeof value === "object" ? (value as Dictionary) : {}
}

export function namesFrom(bundle: Bundle | undefined): RegionNames {
  return {
    region: dictionary(bundle?.regionName),
    city: dictionary(bundle?.cityName),
    alias: dictionary(bundle?.regionAlias),
  }
}

function keywordsFor(
  code: RegionCode,
  locale: Locale,
  names: Readonly<Record<Locale, RegionNames>>,
  withCity: boolean,
): string[] {
  return LOCALES.flatMap((other) => {
    const set = names[other]
    const aliases = splitAliases(set.alias[code])
    if (other === locale) return aliases
    const city = withCity ? set.city[code] : undefined
    return [set.region[code] ?? "", city ?? "", ...aliases].filter((word) => word !== "")
  })
}

export type RegionGroupText = {
  readonly none: string
  readonly cities: string
  readonly regions: string
}

export function buildRegionGroups(
  locale: Locale,
  names: Readonly<Record<Locale, RegionNames>>,
  text: RegionGroupText,
): readonly ComboboxGroup[] {
  const own = names[locale]
  const regionLabel = (code: RegionCode) => own.region[code] ?? code
  const cities = MAJOR_CITY_CODES.filter(isRegionCode).map((code): ComboboxOption => {
    const label = own.city[code] ?? regionLabel(code)
    const region = regionLabel(code)
    return {
      key: `city-${code}`,
      value: code,
      label,
      detail: region === label ? undefined : region,
      keywords: keywordsFor(code, locale, names, true),
    }
  })
  const collator = new Intl.Collator(LOCALE_TAGS[locale])
  const regions = [...REGION_CODES]
    .sort((a, b) => collator.compare(regionLabel(a), regionLabel(b)))
    .map(
      (code): ComboboxOption => ({
        key: `region-${code}`,
        value: code,
        label: regionLabel(code),
        keywords: keywordsFor(code, locale, names, false),
      }),
    )
  return [
    { key: "none", options: [{ key: "none", value: "", label: text.none }] },
    { key: "cities", label: text.cities, options: cities },
    { key: "regions", label: text.regions, options: regions },
  ]
}

export function useRegionGroups(): {
  readonly locale: Locale
  readonly groups: readonly ComboboxGroup[]
} {
  const { t, i18n } = useTranslation("search")
  const locale = toLocale(i18n.language) ?? DEFAULT_LOCALE
  const groups = useMemo(() => {
    const names = Object.fromEntries(
      LOCALES.map((each) => [each, namesFrom(i18n.getResourceBundle(each, "evidence"))]),
    ) as Record<Locale, RegionNames>
    return buildRegionGroups(locale, names, {
      none: t("box.anyRegion"),
      cities: t("box.regionPicker.cities"),
      regions: t("box.regionPicker.regions"),
    })
  }, [i18n, locale, t])
  return { locale, groups }
}
