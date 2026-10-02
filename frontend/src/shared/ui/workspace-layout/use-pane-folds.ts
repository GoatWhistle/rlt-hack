import { useEffect, useRef, useState } from "react"
import { withViewTransition } from "@/shared/motion/view-transition"
import { localJson } from "@/shared/storage/local-json"

export const PANE_FOLDS_KEY = "lotive.workspace.folded"
export const FOLDABLE_PANES = ["list", "candidates"] as const
export type FoldablePane = (typeof FOLDABLE_PANES)[number]
export type PaneFolds = Readonly<Record<FoldablePane, boolean>>

const OPEN: PaneFolds = { list: false, candidates: false }

function readFolds(): PaneFolds {
  const stored = localJson.read(PANE_FOLDS_KEY)
  if (typeof stored !== "object" || stored === null) return OPEN
  const value = stored as Partial<Record<FoldablePane, unknown>>
  return { list: value.list === true, candidates: value.candidates === true }
}

type Moved = { readonly pane: FoldablePane; readonly folded: boolean } | null

export function usePaneFolds(focusPane: (pane: FoldablePane, folded: boolean) => void) {
  const [folds, setFolds] = useState(readFolds)
  const moved = useRef<Moved>(null)
  const focusRef = useRef(focusPane)
  focusRef.current = focusPane

  useEffect(() => {
    const last = moved.current
    moved.current = null
    if (last && folds[last.pane] === last.folded) focusRef.current(last.pane, last.folded)
  }, [folds])

  const change = (pane: FoldablePane, folded: boolean) => {
    const next = { ...folds, [pane]: folded }
    moved.current = { pane, folded }
    localJson.write(PANE_FOLDS_KEY, next)
    withViewTransition(`fold-${pane}`, () => setFolds(next))
  }
  return [folds, change] as const
}
