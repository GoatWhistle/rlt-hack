import type { LotShortlists } from "@/entities/shortlist/store"
import type { LotResult } from "@/entities/upload/model"

export const CSV_TYPE = "text/csv;charset=utf-8"
export const CSV_SEPARATOR = ";"
export const CSV_BOM = "\uFEFF"

export const PRODUCT_COLUMNS = ["lot_id", "product_name", "okpd2_code", "origin"] as const

export const SUPPLIER_COLUMNS = [
  "lot_id",
  "rank",
  "supplier_inn",
  "supplier_name",
  "role",
  "status",
  "check_reason",
  "matched_products",
  "products_total",
  "stock_confirmed",
  "in_catalog",
  "assumed",
  "similar_purchases",
  "wins",
  "summary",
] as const

type Cell = string | number

function cell(value: Cell): string {
  const raw = String(value)
  return /[",;\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw
}

export function toCsv(header: readonly string[], rows: readonly (readonly Cell[])[]): string {
  const lines = [header, ...rows].map((row) => row.map(cell).join(CSV_SEPARATOR))
  return `${CSV_BOM}${lines.join("\r\n")}\r\n`
}

export function productsCsv(results: readonly LotResult[]): string {
  const rows = results.flatMap(({ lot, recommendation }) =>
    (recommendation?.products ?? []).map((product) => [
      lot.id,
      product.name,
      product.okpd2,
      product.origin,
    ]),
  )
  return toCsv(PRODUCT_COLUMNS, rows)
}

export function suppliersCsv(
  results: readonly LotResult[],
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
          company.checkReason ?? "",
          company.matches.length,
          total,
          basis("stock"),
          basis("catalog"),
          basis("inferred"),
          company.similarPurchases ?? "",
          company.wins ?? "",
          company.summary,
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
