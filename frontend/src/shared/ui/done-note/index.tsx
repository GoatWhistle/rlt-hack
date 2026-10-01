import type { ReactNode } from "react"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function DoneNote({ children }: { readonly children: ReactNode }) {
  return (
    <span className={styles.note}>
      <Icon name="check" size="sm" tone="confirmed" />
      {children}
    </span>
  )
}
