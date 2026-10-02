import { checkNotices } from "@/entities/notice/check"
import { decodeFile } from "@/entities/notice/decode"
import type { FileCheck } from "@/entities/notice/model"
import { extensionOf, type Intake, kindOf, MAX_FILE_BYTES } from "./model"

const ZIP = [0x50, 0x4b]
const COMPOUND = [0xd0, 0xcf, 0x11, 0xe0]
const PDF = [0x25, 0x50, 0x44, 0x46]

const SIGNATURES: ReadonlyMap<string, readonly number[]> = new Map([
  ["pdf", PDF],
  ["xlsx", ZIP],
  ["docx", ZIP],
  ["xls", COMPOUND],
  ["doc", COMPOUND],
])

export async function inspectFile(file: File): Promise<FileCheck> {
  try {
    return checkNotices(await decodeFile(file), file.name)
  } catch {
    return { ok: false, fileName: file.name, problem: "unreadable", missing: [] }
  }
}

async function readable(file: File): Promise<boolean> {
  if (file.size === 0) return false
  const signature = SIGNATURES.get(extensionOf(file.name)) ?? []
  try {
    const head = new Uint8Array(await file.slice(0, signature.length || 1).arrayBuffer())
    return signature.every((byte, index) => head[index] === byte)
  } catch {
    return false
  }
}

export async function intakeFile(file: File): Promise<Intake> {
  const kind = kindOf(file.name)
  if (!kind) return { status: "rejected", file, reason: "unsupported" }
  if (file.size > MAX_FILE_BYTES) return { status: "rejected", file, reason: "tooLarge" }
  if (kind === "csv") return { status: "checked", file, check: await inspectFile(file) }
  if (!(await readable(file))) return { status: "rejected", file, reason: "unreadable" }
  return { status: "later", file, kind }
}
