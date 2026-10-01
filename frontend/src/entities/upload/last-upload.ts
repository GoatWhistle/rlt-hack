import { localJson } from "@/shared/storage/local-json"

export const LAST_UPLOAD_KEY = "rlt.lastUpload.v1"

export function readLastUpload(): string | undefined {
  const value = localJson.read(LAST_UPLOAD_KEY)
  return typeof value === "string" ? value : undefined
}

export function rememberUpload(uploadId: string): void {
  localJson.write(LAST_UPLOAD_KEY, uploadId)
}
