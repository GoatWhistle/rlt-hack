import { useCallback, useEffect, useState } from "react"

export function useInView<T extends Element>(): readonly [(node: T | null) => void, boolean] {
  const [node, setNode] = useState<T | null>(null)
  const [inView, setInView] = useState(true)
  const ref = useCallback((next: T | null) => setNode(next), [])

  useEffect(() => {
    if (!node || typeof IntersectionObserver === "undefined") {
      setInView(true)
      return
    }
    const observer = new IntersectionObserver(([entry]) =>
      setInView(entry?.isIntersecting ?? true),
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [node])

  return [ref, inView] as const
}
