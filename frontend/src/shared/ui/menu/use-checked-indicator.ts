import type { RefObject } from "react"
import { useLayoutEffect } from "react"

export const CHECKED_ITEM = '[aria-checked="true"]'

export function placeIndicator(menu: HTMLElement): boolean {
  const checked = menu.querySelector<HTMLElement>(CHECKED_ITEM)
  if (!checked) {
    menu.dataset.indicator = "hidden"
    return false
  }
  if (menu.dataset.indicator !== "ready") menu.dataset.indicator = "placed"
  menu.style.setProperty("--indicator-y", `${checked.offsetTop}px`)
  menu.style.setProperty("--indicator-height", `${checked.offsetHeight}px`)
  return true
}

export function useCheckedIndicator(
  ref: RefObject<HTMLElement | null>,
  mounted: boolean,
): void {
  useLayoutEffect(() => {
    const menu = ref.current
    if (!mounted || !menu) return
    if (!placeIndicator(menu) || menu.dataset.indicator === "ready") return
    const frame = requestAnimationFrame(() => {
      menu.dataset.indicator = "ready"
    })
    return () => cancelAnimationFrame(frame)
  })
}
