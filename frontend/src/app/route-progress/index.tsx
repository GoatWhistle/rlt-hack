import { useEffect, useState } from "react"
import { useNavigation } from "react-router"
import { usePresence } from "@/shared/motion/use-presence"
import styles from "./styles.module.css"

export const ROUTE_PROGRESS_DELAY_MS = 150

export function RouteProgress() {
  const loading = useNavigation().state === "loading"
  const [late, setLate] = useState(false)

  useEffect(() => {
    if (!loading) {
      setLate(false)
      return
    }
    const timer = window.setTimeout(() => setLate(true), ROUTE_PROGRESS_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [loading])

  const { isMounted, state, onAnimationEnd } = usePresence(loading && late)
  if (!isMounted) return null
  return (
    <span
      className={styles.bar}
      data-state={state}
      aria-hidden="true"
      onAnimationEnd={onAnimationEnd}
    />
  )
}
