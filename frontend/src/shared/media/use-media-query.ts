import { useSyncExternalStore } from "react"

function matches(query: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(query).matches
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (listener) => {
      if (typeof window.matchMedia !== "function") return () => {}
      const list = window.matchMedia(query)
      list.addEventListener("change", listener)
      return () => list.removeEventListener("change", listener)
    },
    () => matches(query),
    () => false,
  )
}
