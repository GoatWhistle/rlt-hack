import { useCallback, useEffect, useRef } from "react"
import { useMediaQuery } from "@/shared/media/use-media-query"

export const NARROW_LAYOUT = "(max-width: 47.99rem)"
export const WORKSPACE_VIEWS = ["list", "candidates", "evidence"] as const
export type WorkspaceView = (typeof WORKSPACE_VIEWS)[number]
export const DEFAULT_VIEW: WorkspaceView = "evidence"
export const PANE_HEADING = "h2[tabindex]"

export function parseView(value: string | null): WorkspaceView {
  return WORKSPACE_VIEWS.find((view) => view === value) ?? DEFAULT_VIEW
}

export function viewParam(view: WorkspaceView): string | null {
  return view === DEFAULT_VIEW ? null : view
}

type Pending = { readonly focus: boolean } | null

export function useWorkspaceView(view: WorkspaceView) {
  const narrow = useMediaQuery(NARROW_LAYOUT)
  const stackRef = useRef<HTMLDivElement>(null)
  const pending = useRef<Pending>(null)

  useEffect(() => {
    const next = pending.current
    const stack = stackRef.current
    pending.current = null
    if (!next || !stack || !view) return
    const top = stack.getBoundingClientRect().top
    if (top < 0) window.scrollBy({ top })
    if (next.focus)
      stack.querySelector<HTMLElement>(PANE_HEADING)?.focus({ preventScroll: true })
  }, [view])

  const prepareSwitch = useCallback((focus: boolean) => {
    pending.current = { focus }
  }, [])

  return { narrow, stackRef, prepareSwitch }
}
