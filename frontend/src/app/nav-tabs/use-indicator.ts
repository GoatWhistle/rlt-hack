import { type RefObject, useLayoutEffect, useState } from "react"

export type IndicatorBox = {
  readonly x: number
  readonly width: number
}

const ACTIVE_SELECTOR = "[aria-current='page']"

export function measureActive(root: HTMLElement): IndicatorBox | null {
  const active = root.querySelector<HTMLElement>(ACTIVE_SELECTOR)
  if (!active || active.offsetWidth === 0) return null
  return { x: active.offsetLeft, width: active.offsetWidth }
}

function sameBox(a: IndicatorBox | null, b: IndicatorBox | null): boolean {
  return a?.x === b?.x && a?.width === b?.width
}

export function useIndicator(
  ref: RefObject<HTMLElement | null>,
  activeKey: string | null,
): IndicatorBox | null {
  const [box, setBox] = useState<IndicatorBox | null>(null)

  useLayoutEffect(() => {
    const root = ref.current
    if (!root || activeKey === null) {
      setBox(null)
      return
    }
    const measure = () => {
      const next = measureActive(root)
      setBox((current) => (sameBox(current, next) ? current : next))
    }
    measure()
    if (typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(measure)
    observer.observe(root)
    for (const child of Array.from(root.children)) observer.observe(child)
    return () => observer.disconnect()
  }, [ref, activeKey])

  return box
}
