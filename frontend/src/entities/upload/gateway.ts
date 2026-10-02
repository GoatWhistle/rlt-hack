import type { CheckedFile } from "@/entities/notice/model"
import { ApiError } from "@/shared/api/api-error"
import type { LotDetail, LotResult, UploadDetail, UploadSummary } from "./model"

export type NewUpload = {
  readonly file: File
  readonly itemsFile?: File
  readonly check: CheckedFile
}

export type UploadGateway = {
  readonly list: () => Promise<readonly UploadSummary[]>
  readonly get: (uploadId: string) => Promise<UploadDetail>
  readonly summary?: (uploadId: string) => Promise<UploadSummary>
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
