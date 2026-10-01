import type { CheckedFile } from "@/entities/notice/model"
import { ApiError } from "@/shared/api/api-error"
import type { LotDetail, LotResult, UploadDetail, UploadSummary } from "./model"

export type NewUpload = {
  readonly file: File
  readonly check: CheckedFile
}

export type UploadGateway = {
  readonly demo: boolean
  readonly maxNotices: number
  readonly list: () => Promise<readonly UploadSummary[]>
  readonly get: (uploadId: string) => Promise<UploadDetail>
  readonly create: (upload: NewUpload) => Promise<UploadSummary>
  readonly lot: (uploadId: string, lotId: string) => Promise<LotDetail>
  readonly results: (
    uploadId: string,
    lotIds: readonly string[],
  ) => Promise<readonly LotResult[]>
}

export function notFound(): ApiError {
  return new ApiError({ status: 404, code: "notFound" })
}
