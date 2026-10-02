import type { HttpClient } from "@/shared/api/http-client"
import type { UploadGateway } from "./gateway"
import type { LotResult } from "./model"
import {
  parseLotDetail,
  parseLotResults,
  parseUploadDetail,
  parseUploadList,
  parseUploadSummary,
} from "./parse"

export const UPLOADS_PATH = "/uploads"

function uploadPath(uploadId: string): string {
  return `${UPLOADS_PATH}/${encodeURIComponent(uploadId)}`
}

export function createHttpGateway(client: HttpClient): UploadGateway {
  return {
    list: () => client.get(UPLOADS_PATH, { parse: parseUploadList }),
    get: (uploadId) => client.get(uploadPath(uploadId), { parse: parseUploadDetail }),
    summary: (uploadId) =>
      client.get(`${uploadPath(uploadId)}/summary`, {
        parse: (value) => parseUploadSummary(value),
      }),
    create: ({ file, itemsFile }) => {
      const body = new FormData()
      body.append("file", file)
      if (itemsFile) body.append("items_file", itemsFile)
      return client.post(UPLOADS_PATH, { body, parse: (value) => parseUploadSummary(value) })
    },
    lot: (uploadId, lotId) =>
      client.get(`${uploadPath(uploadId)}/lots/${encodeURIComponent(lotId)}`, {
        parse: parseLotDetail,
      }),
    results: async (uploadId, lotIds) => {
      const results: LotResult[] = []
      for (let offset = 0; offset < lotIds.length; offset += 20) {
        const batch = await client.post(`${uploadPath(uploadId)}/results`, {
          body: { lotIds: lotIds.slice(offset, offset + 20) },
          parse: parseLotResults,
        })
        results.push(...batch)
      }
      return results
    },
  }
}
