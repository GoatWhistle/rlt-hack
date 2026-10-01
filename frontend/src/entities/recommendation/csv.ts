import type { Company, Recommendation } from "./model"

export type CsvColumn = {
  readonly header: string
  readonly value: (company: Company, rank: number) => string | number
}

function cell(value: string | number): string {
  const raw = String(value)
  return /[",;\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw
}

export const CSV_SEPARATOR = ";"
export const CSV_BOM = "﻿"

export function toCsv(recommendation: Recommendation, columns: readonly CsvColumn[]): string {
  const header = columns.map((column) => cell(column.header)).join(CSV_SEPARATOR)
  const rows = recommendation.companies.map((company, index) =>
    columns.map((column) => cell(column.value(company, index + 1))).join(CSV_SEPARATOR),
  )
  return `${CSV_BOM}${[header, ...rows].join("\r\n")}\r\n`
}

export function csvFileName(recommendation: Recommendation): string {
  const stem = recommendation.fileName.replace(/\.[^.]+$/, "") || "recommendation"
  return `${stem}-suppliers.csv`
}
