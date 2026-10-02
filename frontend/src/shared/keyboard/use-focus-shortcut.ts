import { type RefObject, useEffect } from "react"

export const FOCUS_SHORTCUT = "/"

export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

export function focusAtEnd(field: HTMLInputElement | HTMLTextAreaElement | null): void {
  if (!field) return
  field.focus()
  const end = field.value.length
  field.setSelectionRange(end, end)
}

export function useFocusShortcut(
  ref: RefObject<HTMLInputElement | HTMLTextAreaElement | null>,
  enabled = true,
): void {
  useEffect(() => {
    if (!enabled) return
    const focusField = (event: KeyboardEvent) => {
      if (event.key !== FOCUS_SHORTCUT || event.ctrlKey || event.metaKey || event.altKey) return
      if (event.defaultPrevented || isTyping(event.target)) return
      if (document.querySelector("dialog[open]")) return
      event.preventDefault()
      focusAtEnd(ref.current)
    }
    window.addEventListener("keydown", focusField)
    return () => window.removeEventListener("keydown", focusField)
  }, [ref, enabled])
}
