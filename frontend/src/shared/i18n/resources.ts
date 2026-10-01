import type { Locale } from "./locale"
import enCommon from "./locales/en/common.json"
import enErrors from "./locales/en/errors.json"
import enExport from "./locales/en/export.json"
import enLot from "./locales/en/lot.json"
import enLots from "./locales/en/lots.json"
import enNotices from "./locales/en/notices.json"
import enUploads from "./locales/en/uploads.json"
import ruCommon from "./locales/ru/common.json"
import ruErrors from "./locales/ru/errors.json"
import ruExport from "./locales/ru/export.json"
import ruLot from "./locales/ru/lot.json"
import ruLots from "./locales/ru/lots.json"
import ruNotices from "./locales/ru/notices.json"
import ruUploads from "./locales/ru/uploads.json"

export const NAMESPACES = [
  "common",
  "errors",
  "uploads",
  "notices",
  "lots",
  "lot",
  "export",
] as const

export type Namespace = (typeof NAMESPACES)[number]

export const DEFAULT_NAMESPACE = "common" satisfies Namespace

export const resources = {
  ru: {
    common: ruCommon,
    errors: ruErrors,
    uploads: ruUploads,
    notices: ruNotices,
    lots: ruLots,
    lot: ruLot,
    export: ruExport,
  },
  en: {
    common: enCommon,
    errors: enErrors,
    uploads: enUploads,
    notices: enNotices,
    lots: enLots,
    lot: enLot,
    export: enExport,
  },
} satisfies Record<Locale, Record<Namespace, object>>

export type Resources = (typeof resources)["en"]
