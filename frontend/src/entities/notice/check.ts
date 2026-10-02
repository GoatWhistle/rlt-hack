import { readCsv } from "./csv-reader"
import {
  type FileCheck,
  KNOWN_COLUMNS,
  type Notice,
  type NoticeColumn,
  REQUIRED_COLUMNS,
  type RowIssue,
} from "./model"

export const PREVIEW_ROWS = 5

const LOT_ID = /^[0-9A-Za-z_-]+$/
const ISO_DATE = /^\d{4}-\d{2}-\d{2}/

type Cells = (column: NoticeColumn) => string

function normalizeHeader(cell: string): string {
  return cell
    .replace(/^\uFEFF/, "")
    .trim()
    .toLowerCase()
}

export function parsePrice(raw: string): number | undefined | null {
  const compact = raw.replace(/[\s\u00A0]/g, "").replace(",", ".")
  if (compact.length === 0) return undefined
  const value = Number(compact)
  return Number.isFinite(value) && value >= 0 ? value : null
}

function validDate(raw: string): boolean {
  return ISO_DATE.test(raw) && !Number.isNaN(Date.parse(raw.slice(0, 10)))
}

function readNotice(row: number, cell: Cells, seen: Set<string>): Notice | RowIssue[] {
  const issues: RowIssue[] = []
  const lotId = cell("lot_id")
  if (lotId.length === 0) issues.push({ row, code: "missingLotId" })
  else if (!LOT_ID.test(lotId)) issues.push({ row, code: "badLotId", value: lotId })
  else if (seen.has(lotId)) issues.push({ row, code: "duplicateLot", value: lotId })
  const subject = cell("subject")
  const title = cell("procedure_name") || subject
  if (title.length === 0) issues.push({ row, code: "missingTitle" })
  const price = parsePrice(cell("start_price"))
  if (price === null) issues.push({ row, code: "badPrice", value: cell("start_price") })
  const publishDate = cell("publish_date")
  if (publishDate && !validDate(publishDate)) {
    issues.push({ row, code: "badDate", value: publishDate })
  }
  if (issues.length > 0) return issues
  seen.add(lotId)
  const notice: Notice = { lotId, title }
  return Object.assign(
    notice,
    subject && subject !== title ? { subject } : {},
    price === undefined || price === null ? {} : { startPrice: price },
    cell("customer_inn") ? { customerInn: cell("customer_inn") } : {},
    publishDate ? { publishDate: publishDate.slice(0, 10) } : {},
  )
}

export function checkNotices(text: string, fileName: string): FileCheck {
  const records = readCsv(text)
  const [head, ...data] = records
  if (!head) return { ok: false, fileName, problem: "empty", missing: [] }
  const header = head.cells.map(normalizeHeader)
  const missing = REQUIRED_COLUMNS.filter((column) => !header.includes(column))
  if (missing.length > 0) return { ok: false, fileName, problem: "missingColumns", missing }
  if (data.length === 0) return { ok: false, fileName, problem: "empty", missing: [] }

  const known = new Set<string>(KNOWN_COLUMNS)
  const notices: Notice[] = []
  const issues: RowIssue[] = []
  const seen = new Set<string>()
  for (const record of data) {
    if (record.cells.length > header.length) {
      issues.push({ row: record.line, code: "columnCount" })
      continue
    }
    const cell: Cells = (column) => (record.cells[header.indexOf(column)] ?? "").trim()
    const result = readNotice(record.line, cell, seen)
    if (Array.isArray(result)) issues.push(...result)
    else notices.push(result)
  }

  return {
    ok: true,
    fileName,
    columns: head.cells.map((name, index) => ({
      name: name.replace(/^\uFEFF/, "").trim(),
      known: known.has(header[index] ?? ""),
    })),
    preview: data.slice(0, PREVIEW_ROWS).map((record) => ({
      line: record.line,
      cells: header.map((_, index) => record.cells[index]?.trim() ?? ""),
    })),
    total: data.length,
    notices,
    issues,
  }
}
