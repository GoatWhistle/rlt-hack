import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type ScrollRegionProps = {
  readonly label: string
  readonly children: ReactNode
}

export function ScrollRegion({ label, children }: ScrollRegionProps) {
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: a scrollable region must be reachable from the keyboard
    <section className={styles.region} aria-label={label} tabIndex={0}>
      {children}
    </section>
  )
}
