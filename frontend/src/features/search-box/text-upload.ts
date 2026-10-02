import { checkNotices } from "@/entities/notice/check"
import type { NewUpload } from "@/entities/upload/gateway"
import { TEXT_QUERY_FILE, TEXT_QUERY_LOT } from "@/entities/upload/model"

export const SEARCH_LOT_ID = TEXT_QUERY_LOT
const SEARCH_FILE_NAME = TEXT_QUERY_FILE

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
