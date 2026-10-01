export const REQUIRED_COLUMNS = ["lot_id", "procedure_name"] as const

export const KNOWN_COLUMNS = [
  ...REQUIRED_COLUMNS,
  "subject",
  "start_price",
  "customer_inn",
  "customer_kpp",
  "publish_date",
  "procedure_id",
  "reqnum",
  "is_smp",
  "is_eshop_or_aisgz",
] as const

export type NoticeColumn = (typeof KNOWN_COLUMNS)[number]

export type Notice = {
  readonly lotId: string
  readonly title: string
  readonly subject?: string
  readonly startPrice?: number
  readonly customerInn?: string
  readonly publishDate?: string
}

export const ISSUE_CODES = [
  "missingLotId",
  "badLotId",
  "duplicateLot",
  "missingTitle",
  "badPrice",
  "badDate",
  "columnCount",
] as const

export type IssueCode = (typeof ISSUE_CODES)[number]

export type RowIssue = {
  readonly row: number
  readonly code: IssueCode
  readonly value?: string
}

export const FILE_PROBLEMS = ["unreadable", "empty", "missingColumns", "tooManyRows"] as const

export type FileProblem = (typeof FILE_PROBLEMS)[number]

export type HeaderColumn = {
  readonly name: string
  readonly known: boolean
}

export type PreviewRow = {
  readonly line: number
  readonly cells: readonly string[]
}

export type CheckedFile = {
  readonly ok: true
  readonly fileName: string
  readonly columns: readonly HeaderColumn[]
  readonly preview: readonly PreviewRow[]
  readonly total: number
  readonly notices: readonly Notice[]
  readonly issues: readonly RowIssue[]
}

export type RejectedFile = {
  readonly ok: false
  readonly fileName: string
  readonly problem: FileProblem
  readonly missing: readonly string[]
  readonly limit?: number
}

export type FileCheck = CheckedFile | RejectedFile
