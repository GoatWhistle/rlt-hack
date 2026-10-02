import type { ReactNode } from "react"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type DoneNoteProps = {
  readonly pop?: boolean
  readonly icon?: IconName
  readonly children: ReactNode
}

export function DoneNote({ pop = false, icon = "check", children }: DoneNoteProps) {
  return (
    <span className={styles.note}>
      <span className={styles.mark} data-pop={pop || undefined}>
        <Icon name={icon} size="sm" />
      </span>
      {children}
    </span>
  )
}
