import { type RefObject, useLayoutEffect, useState } from "react"

export type IndicatorBox = {
  readonly x: number
  readonly width: number
}

export type Indicator = {
  readonly box: IndicatorBox | null
  readonly animated: boolean
}

const ACTIVE_SELECTOR = "[aria-current='page']"

function padding(value: string): number {
  return Number.parseFloat(value) || 0
}

export function measureActive(root: HTMLElement): IndicatorBox | null {
  const active = root.querySelector<HTMLElement>(ACTIVE_SELECTOR)
  if (!active || active.offsetWidth === 0) return null
  const style = getComputedStyle(active)
  const start = padding(style.paddingInlineStart)
  const end = padding(style.paddingInlineEnd)
  return { x: active.offsetLeft + start, width: active.offsetWidth - start - end }
}

function sameBox(a: IndicatorBox | null, b: IndicatorBox | null): boolean {
  return a?.x === b?.x && a?.width === b?.width
}

export function useIndicator(
  ref: RefObject<HTMLElement | null>,
  activeKey: string | null,
): Indicator {
  const [box, setBox] = useState<IndicatorBox | null>(null)
  const [animated, setAnimated] = useState(false)

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

  useLayoutEffect(() => {
    const root = ref.current
    let frame = 0
    let active = true
    const settle = () => {
      frame = requestAnimationFrame(() => setAnimated(true))
    }
    settle()
    document.fonts?.ready.then(() => {
      if (!active || !root) return
      cancelAnimationFrame(frame)
      setAnimated(false)
      const next = measureActive(root)
      setBox((current) => (sameBox(current, next) ? current : next))
      settle()
    })
    return () => {
      active = false
      cancelAnimationFrame(frame)
    }
  }, [ref])

  return { box, animated }
}
