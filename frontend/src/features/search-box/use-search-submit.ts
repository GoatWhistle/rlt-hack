import type { ReactNode } from "react"
import { useState } from "react"
import type { NewUpload } from "@/entities/upload/gateway"
import type { UploadSummary } from "@/entities/upload/model"
import { useCreateUpload } from "@/entities/upload/queries"
import { isApiError } from "@/shared/api/api-error"
import { FILE_NEEDS_TEXT, problemOf } from "./field-effects"
import { SEARCH_LOT_ID, textUpload } from "./text-upload"

export type Attachment = {
  readonly upload: NewUpload | null
  readonly reading: boolean
  readonly needsText: boolean
  readonly dropping: boolean
  readonly chip: ReactNode
  readonly tool: ReactNode
  readonly hint: ReactNode
}

export type Found = (result: UploadSummary, lots: readonly string[]) => void

function lotsOf(upload: NewUpload): readonly string[] {
  return upload.check.notices.map((notice) => notice.lotId)
}

function staleFileProblem(problem: unknown, attachment: Attachment | undefined): boolean {
  return isApiError(problem) && problem.code === FILE_NEEDS_TEXT && !attachment?.needsText
}

export function isBlocked(attachment: Attachment | undefined, text: string): boolean {
  if (!attachment) return false
  return attachment.reading || (attachment.needsText && text.trim() === "")
}

export function useSearchSubmit(attachment: Attachment | undefined, onFound: Found) {
  const search = useCreateUpload()
  const [problem, setProblem] = useState<unknown>(null)
  const error = (staleFileProblem(problem, attachment) ? null : problem) ?? search.error

  function submit(text: string, region: string) {
    if (search.isPending || attachment?.reading) return
    const file = attachment?.upload
    if (file) {
      setProblem(null)
      search.mutate(file, { onSuccess: (result) => onFound(result, lotsOf(file)) })
      return
    }
    const query = text.trim()
    const found = problemOf(query, attachment?.needsText === true)
    setProblem(found)
    if (found) return
    search.mutate(textUpload(query, region), {
      onSuccess: (result) => onFound(result, [SEARCH_LOT_ID]),
    })
  }

  function clear() {
    setProblem(null)
    if (search.isError) search.reset()
  }

  return { pending: search.isPending, error, submit, clear }
}
