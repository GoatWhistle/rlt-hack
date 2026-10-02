function isScrollable(element: HTMLElement): boolean {
  const { overflowY } = getComputedStyle(element)
  return (
    (overflowY === "auto" || overflowY === "scroll") &&
    element.scrollHeight > element.clientHeight
  )
}

export function scrollPaneOf(element: HTMLElement): HTMLElement | null {
  let pane = element.parentElement
  while (pane && pane !== document.body) {
    if (isScrollable(pane)) return pane
    pane = pane.parentElement
  }
  return null
}

type Area = { readonly top: number; readonly bottom: number; readonly height: number }

function offsetToCenter(box: DOMRect, area: Area): number {
  if (box.top >= area.top && box.bottom <= area.bottom) return 0
  return box.top - area.top - Math.max(0, (area.height - box.height) / 2)
}

export type RevealOptions = {
  readonly window?: boolean
}

export function revealInPane(
  element: HTMLElement | null | undefined,
  options: RevealOptions = {},
): void {
  if (!element) return
  const box = element.getBoundingClientRect()
  const pane = scrollPaneOf(element)
  if (pane) {
    pane.scrollTop += offsetToCenter(box, pane.getBoundingClientRect())
    return
  }
  if (!options.window) return
  const shift = offsetToCenter(box, {
    top: 0,
    bottom: window.innerHeight,
    height: window.innerHeight,
  })
  if (shift !== 0) window.scrollBy({ top: shift, behavior: "instant" })
}
