import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type RevealProps = {
  readonly active: boolean
  readonly children: ReactNode
}

export function Reveal({ active, children }: RevealProps) {
  return (
    <div className={styles.reveal} data-active={active || undefined}>
      {children}
    </div>
  )
}
