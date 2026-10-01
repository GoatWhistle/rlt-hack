import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type PickCardProps = {
  readonly title: string
  readonly subtitle: ReactNode
  readonly rank: number
  readonly selected: boolean
  readonly onSelect: () => void
  readonly children: ReactNode
}

export function PickCard({
  title,
  subtitle,
  rank,
  selected,
  onSelect,
  children,
}: PickCardProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={clsx(styles.card, selected && styles.selected)}
      onClick={onSelect}
    >
      <span className={styles.head}>
        <span className={styles.identity}>
          <span className={styles.title}>{title}</span>
          <span className={styles.subtitle}>{subtitle}</span>
        </span>
        <span className={styles.rank}>{String(rank).padStart(2, "0")}</span>
      </span>
      {children}
    </button>
  )
}
