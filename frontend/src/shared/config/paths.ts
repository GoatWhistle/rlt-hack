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

export const ANALYTICS_PATH = "/analytics"
export const ANALYTICS_CATEGORIES_PATH = `${ANALYTICS_PATH}/categories`
export const ANALYTICS_QUALITY_PATH = `${ANALYTICS_PATH}/quality`
export const ANALYTICS_SOURCES_PATH = `${ANALYTICS_PATH}/sources`
export const ANALYTICS_RECORDS_PATH = `${ANALYTICS_PATH}/records`

export function analyticsCategoryPath(code: string, search = ""): string {
  return `${ANALYTICS_CATEGORIES_PATH}/${encodeURIComponent(code)}${search}`
}

export const HISTORY_PATH = "/history"
export const HISTORY_TAB_PARAM = "tab"
export const HISTORY_TABS = ["queries", "files"] as const
export type HistoryTab = (typeof HISTORY_TABS)[number]

export function historyPath(tab?: HistoryTab): string {
  return tab ? `${HISTORY_PATH}?${HISTORY_TAB_PARAM}=${tab}` : HISTORY_PATH
}
