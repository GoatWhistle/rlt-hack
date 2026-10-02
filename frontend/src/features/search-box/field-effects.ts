import { type RefObject, useEffect } from "react"
import { invalidQuery } from "@/entities/search/gateway"
import { MAX_QUERY_LENGTH } from "@/entities/search/model"
import { isApiError } from "@/shared/api/api-error"
import { focusAtEnd, useFocusShortcut } from "@/shared/keyboard/use-focus-shortcut"
import { useMediaQuery } from "@/shared/media/use-media-query"
import type { SearchStage } from "./use-stage"

export const FINE_POINTER = "(hover: hover) and (pointer: fine)"

const INPUT_PROBLEMS = new Set(["empty_query", "query_too_long", "query_not_understood"])

export function isInputProblem(error: unknown): boolean {
  return isApiError(error) && INPUT_PROBLEMS.has(error.code)
}

export function problemOf(text: string) {
  if (!text) return invalidQuery("empty_query")
  if (text.length > MAX_QUERY_LENGTH) return invalidQuery("query_too_long")
  return null
}

export function joinIds(ids: readonly string[]): string | undefined {
  return ids.filter(Boolean).join(" ") || undefined
}

export function useFieldEffects(
  fieldRef: RefObject<HTMLTextAreaElement | null>,
  { autoFocus, shortcut }: { readonly autoFocus: boolean; readonly shortcut: boolean },
) {
  const finePointer = useMediaQuery(FINE_POINTER)
  useFocusShortcut(fieldRef, shortcut)
  useEffect(() => {
    if (autoFocus && finePointer) focusAtEnd(fieldRef.current)
  }, [fieldRef, autoFocus, finePointer])
}

export function useReportStage(
  stage: SearchStage | null,
  onStage: ((stage: SearchStage | null) => void) | undefined,
) {
  useEffect(() => {
    onStage?.(stage)
  }, [onStage, stage])
}
