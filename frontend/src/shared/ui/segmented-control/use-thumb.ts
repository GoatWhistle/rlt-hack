import { type RefObject, useLayoutEffect, useRef } from "react"

const CHECKED = "input:checked"
const THUMB = "[data-thumb-layer]"

export type ThumbBox = {
  readonly x: number
  readonly y: number
  readonly width: number
  readonly height: number
}

export function placeThumb(group: HTMLElement): ThumbBox | null {
  const option = group.querySelector<HTMLElement>(CHECKED)?.parentElement
  if (!option || option.offsetWidth === 0) {
    group.dataset.thumb = "hidden"
    return null
  }
  const box = {
    x: option.offsetLeft,
    y: option.offsetTop,
    width: option.offsetWidth,
    height: option.offsetHeight,
  }
  group.style.setProperty("--thumb-x", `${box.x}px`)
  group.style.setProperty("--thumb-y", `${box.y}px`)
  group.style.setProperty("--thumb-width", `${box.width}px`)
  group.style.setProperty("--thumb-height", `${box.height}px`)
  group.dataset.thumb = "placed"
  return box
}

function slide(group: HTMLElement, from: ThumbBox, to: ThumbBox): void {
  const thumb = group.querySelector<HTMLElement>(THUMB)
  if (!thumb || typeof thumb.animate !== "function") return
  if (from.x === to.x && from.y === to.y && from.width === to.width) return
  const style = getComputedStyle(group)
  const duration = Number.parseFloat(style.getPropertyValue("--dur-base")) || 0
  const scaleX = from.width / to.width
  const scaleY = from.height / to.height
  thumb.animate(
    [
      {
        transform: `translate(${from.x - to.x}px, ${from.y - to.y}px) scale(${scaleX}, ${scaleY})`,
      },
      { transform: "none" },
    ],
    { duration, easing: style.getPropertyValue("--ease-out").trim() || "ease-out" },
  )
}

export function useThumb(ref: RefObject<HTMLElement | null>, value: string): void {
  const previous = useRef<ThumbBox | null>(null)
  // biome-ignore lint/correctness/useExhaustiveDependencies: the thumb moves when the checked value changes
  useLayoutEffect(() => {
    const group = ref.current
    if (!group) return
    const box = placeThumb(group)
    if (box && previous.current) slide(group, previous.current, box)
    previous.current = box
    if (typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(() => {
      previous.current = placeThumb(group)
    })
    observer.observe(group)
    return () => observer.disconnect()
  }, [ref, value])
}
