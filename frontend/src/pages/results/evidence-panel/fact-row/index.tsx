import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type FactRowProps = {
  readonly title: string
  readonly emphasis?: boolean
  readonly tag: ReactNode
  readonly children?: ReactNode
}

export function FactRow({ title, emphasis = false, tag, children }: FactRowProps) {
  return (
    <div className={styles.row}>
      <div className={styles.head}>
        <span className={clsx(styles.title, emphasis && styles.emphasis)}>{title}</span>
        {tag}
      </div>
      {children}
    </div>
  )
}
