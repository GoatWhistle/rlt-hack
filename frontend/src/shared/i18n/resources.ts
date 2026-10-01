import type { Locale } from "./locale"
import enCommon from "./locales/en/common.json"
import enErrors from "./locales/en/errors.json"
import ruCommon from "./locales/ru/common.json"
import ruErrors from "./locales/ru/errors.json"

export const NAMESPACES = ["common", "errors"] as const

export type Namespace = (typeof NAMESPACES)[number]

export const DEFAULT_NAMESPACE = "common" satisfies Namespace

export const resources = {
  ru: { common: ruCommon, errors: ruErrors },
  en: { common: enCommon, errors: enErrors },
} satisfies Record<Locale, Record<Namespace, object>>

export type Resources = (typeof resources)["en"]
