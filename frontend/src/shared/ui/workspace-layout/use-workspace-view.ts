import { useCallback, useRef, useState } from "react"
import { useMediaQuery } from "@/shared/media/use-media-query"

export const NARROW_LAYOUT = "(max-width: 47.99rem)"
export const WORKSPACE_VIEWS = ["list", "candidates", "evidence"] as const
export type WorkspaceView = (typeof WORKSPACE_VIEWS)[number]

export function useWorkspaceView(initial: WorkspaceView = "evidence") {
  const narrow = useMediaQuery(NARROW_LAYOUT)
  const [view, setView] = useState<WorkspaceView>(initial)
  const stackRef = useRef<HTMLDivElement>(null)
  const show = useCallback((next: WorkspaceView) => {
    setView(next)
    const top = stackRef.current?.getBoundingClientRect().top ?? 0
    if (top < 0) window.scrollBy({ top })
  }, [])
  return { narrow, view, show, stackRef }
}
