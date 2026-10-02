import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type PanelBlockProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly framed?: boolean
  readonly children: ReactNode
}

export function PanelBlock({ title, aside, framed = false, children }: PanelBlockProps) {
  return (
    <section className={clsx(styles.block, framed && styles.framed)}>
      <div className={styles.heading}>
        <h3 className={styles.title}>{title}</h3>
        {aside ? <span className={styles.aside}>{aside}</span> : null}
      </div>
      {children}
    </section>
  )
}
