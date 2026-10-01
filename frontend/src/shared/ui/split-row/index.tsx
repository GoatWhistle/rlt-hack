import type { ReactNode } from "react"
import styles from "./styles.module.css"

export function SplitRow({ children }: { readonly children: ReactNode }) {
  return <div className={styles.row}>{children}</div>
}
