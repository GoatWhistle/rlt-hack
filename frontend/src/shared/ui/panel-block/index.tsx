import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type PanelBlockProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly children: ReactNode
}

export function PanelBlock({ title, aside, children }: PanelBlockProps) {
  return (
    <section className={styles.block}>
      <div className={styles.heading}>
        <h3 className={styles.title}>{title}</h3>
        {aside ? <span className={styles.aside}>{aside}</span> : null}
      </div>
      {children}
    </section>
  )
}
