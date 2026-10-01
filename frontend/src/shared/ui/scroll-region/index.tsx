import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type ScrollRegionProps = {
  readonly label: string
  readonly children: ReactNode
  readonly className?: string
}

export function ScrollRegion({ label, children, className }: ScrollRegionProps) {
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: a scrollable region must be reachable from the keyboard
    <section className={clsx(styles.region, className)} aria-label={label} tabIndex={0}>
      {children}
    </section>
  )
}
