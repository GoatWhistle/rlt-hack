import type { Locale } from "./locale"
import enAnalytics from "./locales/en/analytics.json"
import enCandidate from "./locales/en/candidate.json"
import enCommon from "./locales/en/common.json"
import enErrors from "./locales/en/errors.json"
import enEvidence from "./locales/en/evidence.json"
import enExport from "./locales/en/export.json"
import enLot from "./locales/en/lot.json"
import enLots from "./locales/en/lots.json"
import enNotices from "./locales/en/notices.json"
import enSearch from "./locales/en/search.json"
import enSupplier from "./locales/en/supplier.json"
import enUploads from "./locales/en/uploads.json"
import ruAnalytics from "./locales/ru/analytics.json"
import ruCandidate from "./locales/ru/candidate.json"
import ruCommon from "./locales/ru/common.json"
import ruErrors from "./locales/ru/errors.json"
import ruEvidence from "./locales/ru/evidence.json"
import ruExport from "./locales/ru/export.json"
import ruLot from "./locales/ru/lot.json"
import ruLots from "./locales/ru/lots.json"
import ruNotices from "./locales/ru/notices.json"
import ruSearch from "./locales/ru/search.json"
import ruSupplier from "./locales/ru/supplier.json"
import ruUploads from "./locales/ru/uploads.json"

export const NAMESPACES = [
  "common",
  "errors",
  "uploads",
  "notices",
  "lots",
  "lot",
  "export",
  "evidence",
  "candidate",
  "search",
  "supplier",
  "analytics",
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
    evidence: ruEvidence,
    candidate: ruCandidate,
    search: ruSearch,
    supplier: ruSupplier,
    analytics: ruAnalytics,
  },
  en: {
    common: enCommon,
    errors: enErrors,
    uploads: enUploads,
    notices: enNotices,
    lots: enLots,
    lot: enLot,
    export: enExport,
    evidence: enEvidence,
    candidate: enCandidate,
    search: enSearch,
    supplier: enSupplier,
    analytics: enAnalytics,
  },
} satisfies Record<Locale, Record<Namespace, object>>

export type Resources = (typeof resources)["en"]
