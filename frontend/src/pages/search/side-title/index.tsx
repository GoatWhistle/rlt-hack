import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type SideTitleProps = {
  readonly id?: string
  readonly children: ReactNode
}

export function SideTitle({ id, children }: SideTitleProps) {
  return (
    <h2 id={id} className={styles.title}>
      {children}
    </h2>
  )
}
