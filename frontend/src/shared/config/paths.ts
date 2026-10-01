export const UPLOADS_PATH = "/uploads"
export const LOTS_ENTRY_PATH = "/lots"

export function uploadPath(uploadId: string, search = ""): string {
  return `${UPLOADS_PATH}/${encodeURIComponent(uploadId)}${search}`
}

export function lotPath(uploadId: string, lotId: string, search = ""): string {
  return `${uploadPath(uploadId)}/lots/${encodeURIComponent(lotId)}${search}`
}
