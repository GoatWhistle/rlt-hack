export const PAGE_STEP = 8

export function nextActive(key: string, current: number, count: number): number | null {
  if (count === 0) return null
  const from = Math.max(current, 0)
  switch (key) {
    case "ArrowDown":
      return current < 0 ? 0 : (current + 1) % count
    case "ArrowUp":
      return current < 0 ? count - 1 : (current - 1 + count) % count
    case "Home":
      return 0
    case "End":
      return count - 1
    case "PageDown":
      return Math.min(count - 1, from + PAGE_STEP)
    case "PageUp":
      return Math.max(0, from - PAGE_STEP)
    default:
      return null
  }
}

export function isTypeahead(event: {
  readonly key: string
  readonly ctrlKey: boolean
  readonly metaKey: boolean
  readonly altKey: boolean
}): boolean {
  return (
    event.key.length === 1 &&
    event.key !== " " &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.altKey
  )
}

export const HEADING_SELECTOR = "[data-heading]"

export function revealOption(
  list: HTMLElement | null,
  option: HTMLElement | null,
  center: boolean,
): void {
  if (!list || !option) return
  const top = option.offsetTop
  const bottom = top + option.offsetHeight
  if (center) {
    list.scrollTop = top - (list.clientHeight - option.offsetHeight) / 2
    return
  }
  const heading = option.parentElement?.querySelector<HTMLElement>(HEADING_SELECTOR)
  const cover = heading?.offsetHeight ?? 0
  if (top - cover < list.scrollTop) list.scrollTop = top - cover
  else if (bottom > list.scrollTop + list.clientHeight)
    list.scrollTop = bottom - list.clientHeight
}
