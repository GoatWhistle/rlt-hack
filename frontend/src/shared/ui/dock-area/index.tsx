import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type DockAreaProps = {
  readonly docked: boolean
  readonly children: ReactNode
}

export function DockArea({ docked, children }: DockAreaProps) {
  return (
    <div className={styles.area} data-docked={docked || undefined}>
      {children}
    </div>
  )
}
