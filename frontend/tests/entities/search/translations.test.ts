import { type Tree, text } from "@tests/support/dictionaries"
import { describe, expect, it } from "vitest"
import {
  CANDIDATE_STATUSES,
  CHECK_REASONS,
  COMPANY_ROLES,
  HIGHLIGHT_CODES,
  ITEM_ORIGINS,
  MATCH_BASES,
  PURCHASE_OUTCOMES,
  SOURCE_KINDS,
  WARNING_CODES,
} from "@/entities/search/model"
import { AVAILABILITIES, IDENTITY_STATUSES } from "@/entities/supplier/model"
import { FILTERS } from "@/entities/upload/list-query"
import { LOT_STATUSES, RESULT_STATUSES } from "@/entities/upload/model"
import { LOCALES } from "@/shared/i18n/locale"
import { type Namespace, resources } from "@/shared/i18n/resources"

type Family = readonly [Namespace, string, readonly string[]]

const UPLOAD_ERRORS = [
  "missing_file",
  "file_too_large",
  "unsupported_file_type",
  "invalid_file",
  "missing_columns",
  "too_many_rows",
  "no_valid_lots",
  "upload_not_found",
  "lot_not_found",
] as const

const FAMILIES: readonly Family[] = [
  ["evidence", "checkReason", CHECK_REASONS],
  ["evidence", "highlight", HIGHLIGHT_CODES],
  ["lots", "status", LOT_STATUSES],
  ["lots", "filter", FILTERS],
  ["uploads", "list", RESULT_STATUSES],
  ["errors", "", UPLOAD_ERRORS],
  ["search", "warning", WARNING_CODES],
  ["search", "items.origin", ITEM_ORIGINS],
  ["evidence", "role", COMPANY_ROLES],
  ["evidence", "basis", MATCH_BASES],
  ["evidence", "sourceKind", SOURCE_KINDS],
  ["evidence", "outcome", PURCHASE_OUTCOMES],
  ["evidence", "status", CANDIDATE_STATUSES],
  ["supplier", "availability", AVAILABILITIES],
  ["supplier", "identity", IDENTITY_STATUSES],
]

function translated(locale: (typeof LOCALES)[number], namespace: Namespace, key: string) {
  const parts = key.split(".").filter(Boolean)
  const parent = parts.slice(0, -1)
  const leaf = parts.at(-1) ?? ""
  const node = parent.reduce<Tree | string | undefined>(
    (current, part) => (current && typeof current === "object" ? current[part] : undefined),
    resources[locale][namespace] as Tree,
  )
  if (!node || typeof node !== "object") return false
  return [leaf, `${leaf}_one`].some((name) => typeof node[name] === "string")
}

describe("every code from the search and upload contracts", () => {
  it.each(FAMILIES)("has a %s:%s translation in every language", (namespace, prefix, codes) => {
    for (const locale of LOCALES) {
      const missing = codes.filter(
        (code) => !translated(locale, namespace, `${prefix}.${code}`),
      )
      expect(missing, `${locale}/${namespace}:${prefix}`).toEqual([])
    }
  })

  it("speaks human language, not codes", () => {
    expect(text("ru", "evidence", "checkReason.innMissing")).not.toContain("innMissing")
    expect(text("en", "evidence", "role.serviceProvider")).toBe("Service provider")
  })
})
