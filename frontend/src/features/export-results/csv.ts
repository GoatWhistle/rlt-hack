import type { CheckReason, Highlight } from "@/entities/evidence/model"
import type { CompanyStatus, ProductOrigin } from "@/entities/recommendation/model"
import type { LotShortlists } from "@/entities/shortlist/store"
import type { LotResult } from "@/entities/upload/model"

export const CSV_TYPE = "text/csv;charset=utf-8"
export const CSV_SEPARATOR = ";"
export const CSV_BOM = "\uFEFF"
export const CODE_SEPARATOR = ","
export const NOTE_SEPARATOR = " "
export const SUMMARY_SEPARATOR = " \u00B7 "

export type CsvLabels = {
  readonly checkReason: (reason: CheckReason) => string
  readonly highlight: (highlight: Highlight) => string
}

export type LotCsvLabels = {
  readonly status: (status: CompanyStatus) => string
  readonly origin: (origin: ProductOrigin) => string
}

export const PRODUCT_COLUMNS = [
  "lot_id",
  "product_name",
  "okpd2_code",
  "origin",
  "origin_text",
] as const

export const SUPPLIER_COLUMNS = [
  "lot_id",
  "rank",
  "supplier_inn",
  "supplier_name",
  "role",
  "status",
  "status_text",
  "check_reason",
  "matched_products",
  "products_total",
  "stock_confirmed",
  "in_catalog",
  "assumed",
  "similar_purchases",
  "wins",
  "summary",
  "clarify",
] as const

type Cell = string | number

const FORMULA_START = /^[=+\-@\t\r]/

function cell(value: Cell): string {
  const raw =
    typeof value === "string" && FORMULA_START.test(value) ? `'${value}` : String(value)
  return /[",;\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw
}

export function toCsv(header: readonly string[], rows: readonly (readonly Cell[])[]): string {
  const lines = [header, ...rows].map((row) => row.map(cell).join(CSV_SEPARATOR))
  return `${CSV_BOM}${lines.join("\r\n")}\r\n`
}

export function productsCsv(results: readonly LotResult[], labels: LotCsvLabels): string {
  const rows = results.flatMap(({ lot, recommendation }) =>
    (recommendation?.products ?? []).map((product) => [
      lot.id,
      product.name,
      product.okpd2,
      product.origin,
      labels.origin(product.origin),
    ]),
  )
  return toCsv(PRODUCT_COLUMNS, rows)
}

export function suppliersCsv(
  results: readonly LotResult[],
  labels: LotCsvLabels,
  shortlists?: LotShortlists,
): string {
  const rows = results.flatMap(({ lot, recommendation }) => {
    if (!recommendation) return []
    const total = recommendation.products.length
    const chosen = shortlists ? new Set(shortlists[lot.id] ?? []) : undefined
    return recommendation.companies.flatMap((company, index) => {
      if (chosen && !chosen.has(company.id)) return []
      const basis = (kind: string) => company.matches.filter((m) => m.basis === kind).length
      return [
        [
          lot.id,
          index + 1,
          company.inn,
          company.name,
          company.role,
          company.status,
          labels.status(company.status),
          company.checkReason ?? "",
          company.matches.length - basis("inferred"),
          total,
          basis("stock"),
          basis("catalog"),
          basis("inferred"),
          company.similarPurchases ?? "",
          company.wins ?? "",
          company.summary,
          company.clarify.join(SUMMARY_SEPARATOR),
        ],
      ]
    })
  })
  return toCsv(SUPPLIER_COLUMNS, rows)
}

export function exportFileNames(fileName: string): { products: string; suppliers: string } {
  const stem = fileName.replace(/\.[^.]+$/, "") || "results"
  return { products: `${stem}-products.csv`, suppliers: `${stem}-suppliers.csv` }
}
