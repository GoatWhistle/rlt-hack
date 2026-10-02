import { type RefObject, useEffect, useLayoutEffect } from "react"

function markOverflow(field: HTMLTextAreaElement): void {
  field.toggleAttribute("data-overflow", field.scrollHeight > field.clientHeight + 1)
}

export function useAutoHeight(ref: RefObject<HTMLTextAreaElement | null>, value: string): void {
  useLayoutEffect(() => {
    const field = ref.current
    if (!field || value === undefined) return
    field.style.height = "auto"
    if (field.scrollHeight > 0) field.style.height = `${field.scrollHeight}px`
    markOverflow(field)
  }, [ref, value])

  useEffect(() => {
    const field = ref.current
    if (!field) return
    const measure = () => markOverflow(field)
    field.addEventListener("focus", measure)
    field.addEventListener("blur", measure)
    window.addEventListener("resize", measure)
    return () => {
      field.removeEventListener("focus", measure)
      field.removeEventListener("blur", measure)
      window.removeEventListener("resize", measure)
    }
  }, [ref])
}
