import type { CheckReason, Highlight } from "@/entities/evidence/model"
import type { LotResult } from "@/entities/upload/model"
import { candidateRows, SEARCH_COLUMNS } from "./search-rows"

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

export const PRODUCT_COLUMNS = [
  "lot_id",
  "search_id",
  "item_name",
  "okpd2_code",
  "origin",
] as const

export type Cell = string | number

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

export function productsCsv(results: readonly LotResult[]): string {
  const rows = results.flatMap(({ lot, search }) =>
    (search?.items ?? []).map((item) => [
      lot.id,
      search?.searchId ?? "",
      item.name,
      item.okpd2,
      item.origin,
    ]),
  )
  return toCsv(PRODUCT_COLUMNS, rows)
}

export function suppliersCsv(
  results: readonly LotResult[],
  labels: CsvLabels,
  chosen?: (searchId: string) => readonly string[],
): string {
  const rows = results.flatMap(({ lot, search }) =>
    search
      ? candidateRows(search, labels, chosen?.(search.searchId)).map((row) => [lot.id, ...row])
      : [],
  )
  return toCsv(["lot_id", ...SEARCH_COLUMNS], rows)
}

export function exportFileNames(fileName: string): { products: string; suppliers: string } {
  const stem = fileName.replace(/\.[^.]+$/, "") || "results"
  return { products: `${stem}-products.csv`, suppliers: `${stem}-suppliers.csv` }
}
