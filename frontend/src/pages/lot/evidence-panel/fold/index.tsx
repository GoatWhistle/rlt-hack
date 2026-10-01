import type { ReactNode } from "react"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type FoldProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly children: ReactNode
}

export function Fold({ title, aside, children }: FoldProps) {
  return (
    <details className={styles.fold}>
      <summary className={styles.summary}>
        <h3 className={styles.title}>{title}</h3>
        {aside ? <span className={styles.aside}>{aside}</span> : null}
        <span className={styles.chevron} aria-hidden="true">
          <Icon name="chevron" size="sm" />
        </span>
      </summary>
      <div className={styles.content}>{children}</div>
    </details>
  )
}
