import { checkNotices } from "@/entities/notice/check"
import type { NewUpload } from "@/entities/upload/gateway"

export const SEARCH_LOT_ID = "query"
const SEARCH_FILE_NAME = "search.csv"

function cell(value: string): string {
  return `"${value.replaceAll('"', '""')}"`
}

export function textUpload(text: string, region: string): NewUpload {
  const csv = `lot_id;procedure_name;delivery_region\n${SEARCH_LOT_ID};${cell(text)};${cell(region)}\n`
  const check = checkNotices(csv, SEARCH_FILE_NAME)
  if (!check.ok || check.issues.length > 0) throw new Error("invalid search CSV")
  return {
    file: new File([csv], SEARCH_FILE_NAME, { type: "text/csv" }),
    check,
  }
}
