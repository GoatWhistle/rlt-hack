import type { Notice, RowIssue } from "@/entities/notice/model"
import { type JsonStorage, localJson } from "@/shared/storage/local-json"

export const UPLOADS_KEY = "rlt.uploads.v1"

export type StoredUpload = {
  readonly id: string
  readonly fileName: string
  readonly createdAt: string
  readonly startedAt: number
  readonly notices: readonly Notice[]
  readonly issues: readonly RowIssue[]
}

export type UploadStore = {
  readonly all: () => readonly StoredUpload[]
  readonly find: (id: string) => StoredUpload | undefined
  readonly add: (upload: StoredUpload) => boolean
  readonly isStored: (id: string) => boolean
}

function isStoredUpload(value: unknown): value is StoredUpload {
  if (typeof value !== "object" || value === null) return false
  const entry = value as Record<string, unknown>
  return (
    typeof entry.id === "string" &&
    typeof entry.fileName === "string" &&
    typeof entry.createdAt === "string" &&
    typeof entry.startedAt === "number" &&
    Array.isArray(entry.notices) &&
    Array.isArray(entry.issues)
  )
}

export function createUploadStore(storage: JsonStorage = localJson): UploadStore {
  const saved = storage.read(UPLOADS_KEY)
  let uploads: StoredUpload[] = Array.isArray(saved) ? saved.filter(isStoredUpload) : []
  const transient = new Set<string>()
  return {
    all: () => uploads,
    find: (id) => uploads.find((upload) => upload.id === id),
    add: (upload) => {
      uploads = [upload, ...uploads]
      const stored = storage.write(
        UPLOADS_KEY,
        uploads.filter((entry) => !transient.has(entry.id)),
      )
      if (!stored) transient.add(upload.id)
      return stored
    },
    isStored: (id) => !transient.has(id),
  }
}
