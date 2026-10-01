import { type RefObject, useLayoutEffect } from "react"

export function useAutoHeight(ref: RefObject<HTMLTextAreaElement | null>, value: string): void {
  useLayoutEffect(() => {
    const field = ref.current
    if (!field || value === undefined) return
    field.style.height = "auto"
    if (field.scrollHeight > 0) field.style.height = `${field.scrollHeight}px`
  }, [ref, value])
}
