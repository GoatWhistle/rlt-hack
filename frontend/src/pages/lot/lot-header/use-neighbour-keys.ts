import { useEffect } from "react"
import { useNavigate } from "react-router"

export const PREV_KEY = "["
export const NEXT_KEY = "]"

const CODES: Readonly<Record<string, typeof PREV_KEY | typeof NEXT_KEY>> = {
  BracketLeft: PREV_KEY,
  BracketRight: NEXT_KEY,
}

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable || target.closest("dialog")) return true
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

function wanted(event: KeyboardEvent): string | undefined {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return undefined
  if (typing(event.target)) return undefined
  return CODES[event.code] ?? event.key
}

export function useNeighbourKeys(prev: string | undefined, next: string | undefined) {
  const navigate = useNavigate()
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const key = wanted(event)
      const target = key === PREV_KEY ? prev : key === NEXT_KEY ? next : undefined
      if (!target) return
      event.preventDefault()
      void navigate(target)
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [prev, next, navigate])
}
