import type { ReactNode } from "react"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type DoneNoteProps = {
  readonly pop?: boolean
  readonly children: ReactNode
}

export function DoneNote({ pop = false, children }: DoneNoteProps) {
  return (
    <span className={styles.note}>
      <span className={styles.mark} data-pop={pop || undefined}>
        <Icon name="check" size="sm" />
      </span>
      {children}
    </span>
  )
}
