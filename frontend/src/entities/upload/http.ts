import type { HttpClient } from "@/shared/api/http-client"
import type { UploadGateway } from "./gateway"
import {
  parseLotDetail,
  parseLotResults,
  parseUploadDetail,
  parseUploadList,
  parseUploadSummary,
} from "./parse"

export const UPLOADS_PATH = "/uploads"
export const HTTP_MAX_NOTICES = 500

function uploadPath(uploadId: string): string {
  return `${UPLOADS_PATH}/${encodeURIComponent(uploadId)}`
}

export function createHttpGateway(client: HttpClient): UploadGateway {
  return {
    maxNotices: HTTP_MAX_NOTICES,
    list: () => client.get(UPLOADS_PATH, { parse: parseUploadList }),
    get: (uploadId) => client.get(uploadPath(uploadId), { parse: parseUploadDetail }),
    summary: (uploadId) =>
      client.get(`${uploadPath(uploadId)}/summary`, {
        parse: (value) => parseUploadSummary(value),
      }),
    create: ({ file }) => {
      const body = new FormData()
      body.append("file", file)
      return client.post(UPLOADS_PATH, { body, parse: (value) => parseUploadSummary(value) })
    },
    lot: (uploadId, lotId) =>
      client.get(`${uploadPath(uploadId)}/lots/${encodeURIComponent(lotId)}`, {
        parse: parseLotDetail,
      }),
    results: (uploadId, lotIds) =>
      client.post(`${uploadPath(uploadId)}/results`, {
        body: { lotIds },
        parse: parseLotResults,
      }),
  }
}
