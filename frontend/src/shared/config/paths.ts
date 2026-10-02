export const UPLOADS_PATH = "/uploads"
export const LOTS_ENTRY_PATH = "/lots"
export const NOTICES_SAMPLE_PATH = "/notices-sample.csv"

export function uploadPath(uploadId: string, search = ""): string {
  return `${UPLOADS_PATH}/${encodeURIComponent(uploadId)}${search}`
}

export function lotPath(uploadId: string, lotId: string, search = ""): string {
  return `${uploadPath(uploadId)}/lots/${encodeURIComponent(lotId)}${search}`
}

export const SEARCH_PATH = "/search"
export const SEARCH_TEXT_PARAM = "q"

export function searchPath(searchId: string): string {
  return `${SEARCH_PATH}/${encodeURIComponent(searchId)}`
}

export function searchDraftPath(text: string, region = ""): string {
  return `${SEARCH_PATH}?${new URLSearchParams({ [SEARCH_TEXT_PARAM]: text, ...(region ? { region } : {}) }).toString()}`
}
