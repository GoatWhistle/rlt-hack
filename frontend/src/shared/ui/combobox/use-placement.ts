import { type RefObject, useLayoutEffect } from "react"

export const SHEET_QUERY = "(max-width: 47.99rem)"
export const EDGE = 8
export const MIN_ROOM_REM = 15

export type Side = "bottom" | "top" | "sheet"

function isSheet(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(SHEET_QUERY).matches
}

function rem(): number {
  return Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
}

export function sideFor(below: number, above: number, minRoom: number): Exclude<Side, "sheet"> {
  return below >= minRoom || below >= above ? "bottom" : "top"
}

export function shiftFor(left: number, width: number, viewport: number): number {
  const overflow = left + width - (viewport - EDGE)
  if (overflow <= 0) return 0
  return -Math.min(overflow, Math.max(left - EDGE, 0))
}

export function place(panel: HTMLElement, trigger: HTMLElement): Side {
  if (isSheet()) {
    panel.dataset.side = "sheet"
    return "sheet"
  }
  const box = trigger.getBoundingClientRect()
  const below = window.innerHeight - box.bottom - 2 * EDGE
  const above = box.top - 2 * EDGE
  const side = sideFor(below, above, MIN_ROOM_REM * rem())
  const room = Math.max(side === "bottom" ? below : above, 0)
  const shift = shiftFor(box.left, panel.offsetWidth, document.documentElement.clientWidth)
  panel.style.setProperty("--combobox-room", `${Math.floor(room)}px`)
  panel.style.setProperty("--combobox-shift", `${Math.round(shift)}px`)
  panel.dataset.side = side
  return side
}

export function usePlacement(
  panelRef: RefObject<HTMLElement | null>,
  triggerRef: RefObject<HTMLElement | null>,
  open: boolean,
): void {
  useLayoutEffect(() => {
    if (!open) return
    const update = () => {
      if (panelRef.current && triggerRef.current) place(panelRef.current, triggerRef.current)
    }
    update()
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [open, panelRef, triggerRef])
}
