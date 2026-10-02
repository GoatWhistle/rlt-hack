import type { FileCheck } from "@/entities/notice/model"
import type { NewUpload } from "@/entities/upload/gateway"

export const MAX_FILE_MB = 10
export const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024

export type FileKind = "csv" | "sheet" | "pdf" | "document" | "text"

const EXTENSIONS: ReadonlyMap<string, FileKind> = new Map([
  ["csv", "csv"],
  ["xlsx", "sheet"],
  ["xls", "sheet"],
  ["pdf", "pdf"],
  ["docx", "document"],
  ["doc", "document"],
  ["txt", "text"],
])

export const ACCEPTED_FILES = [...EXTENSIONS.keys()]
  .map((extension) => `.${extension}`)
  .join(",")

export type Rejection = "tooLarge" | "unsupported" | "unreadable"

export type Intake =
  | { readonly status: "reading"; readonly file: File }
  | { readonly status: "checked"; readonly file: File; readonly check: FileCheck }
  | { readonly status: "later"; readonly file: File; readonly kind: FileKind }
  | { readonly status: "rejected"; readonly file: File; readonly reason: Rejection }

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".")
  return dot > 0 ? name.slice(dot + 1).toLowerCase() : ""
}

export function kindOf(name: string): FileKind | undefined {
  return EXTENSIONS.get(extensionOf(name))
}

export function sendable(intake: Intake | null): NewUpload | null {
  if (intake?.status !== "checked" || !intake.check.ok) return null
  if (intake.check.notices.length === 0) return null
  return { file: intake.file, check: intake.check }
}

export function lotsOf(upload: NewUpload): readonly string[] {
  return upload.check.ok ? upload.check.notices.map((notice) => notice.lotId) : []
}

export type SizeUnit = "b" | "kb" | "mb"

export function sizeOf(bytes: number): { readonly unit: SizeUnit; readonly value: number } {
  if (bytes < 1024) return { unit: "b", value: bytes }
  if (bytes < 1024 * 1024) return { unit: "kb", value: Math.round(bytes / 1024) }
  return { unit: "mb", value: Math.round((bytes / (1024 * 1024)) * 10) / 10 }
}

export function splitName(name: string, tail = 6): readonly [string, string] {
  const extension = extensionOf(name)
  const cut = Math.max(0, name.length - (extension ? extension.length + 1 : 0) - tail)
  return [name.slice(0, cut), name.slice(cut)]
}
