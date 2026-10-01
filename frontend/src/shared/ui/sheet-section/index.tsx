import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type SheetSectionProps = {
  readonly title: string
  readonly children: ReactNode
}

export function SheetSection({ title, children }: SheetSectionProps) {
  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>{title}</h3>
      {children}
    </section>
  )
}
