import { type RefObject, useLayoutEffect } from "react"

const CHECKED = "input:checked"

export function placeThumb(group: HTMLElement): boolean {
  const option = group.querySelector<HTMLElement>(CHECKED)?.parentElement
  if (!option || option.offsetWidth === 0) {
    group.dataset.thumb = "hidden"
    return false
  }
  const width = Math.max(group.scrollWidth, group.clientWidth)
  const height = Math.max(group.scrollHeight, group.clientHeight)
  const right = width - option.offsetLeft - option.offsetWidth
  const bottom = height - option.offsetTop - option.offsetHeight
  group.style.setProperty("--thumb-span", `${width}px`)
  group.style.setProperty(
    "--thumb-inset",
    `${option.offsetTop}px ${right}px ${bottom}px ${option.offsetLeft}px`,
  )
  if (group.dataset.thumb !== "ready") group.dataset.thumb = "placed"
  return true
}

export function useThumb(ref: RefObject<HTMLElement | null>, value: string): void {
  // biome-ignore lint/correctness/useExhaustiveDependencies: the thumb moves when the checked value changes
  useLayoutEffect(() => {
    const group = ref.current
    if (!group || !placeThumb(group)) return
    let frame = 0
    if (group.dataset.thumb !== "ready") {
      frame = requestAnimationFrame(() => {
        group.dataset.thumb = "ready"
      })
    }
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => placeThumb(group))
    observer?.observe(group)
    return () => {
      cancelAnimationFrame(frame)
      observer?.disconnect()
    }
  }, [ref, value])
}
