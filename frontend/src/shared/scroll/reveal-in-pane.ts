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

export function revealInPane(element: HTMLElement | null | undefined): void {
  if (!element) return
  const pane = scrollPaneOf(element)
  if (!pane) return
  const box = element.getBoundingClientRect()
  const area = pane.getBoundingClientRect()
  if (box.top >= area.top && box.bottom <= area.bottom) return
  pane.scrollTop += box.top - area.top - Math.max(0, (area.height - box.height) / 2)
}
