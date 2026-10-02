import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type MetricCardProps = {
  readonly label: string
  readonly value: string
  readonly basis?: string
  readonly note?: string
  readonly hint: string
  readonly empty?: boolean
  readonly action?: ReactNode
}

export function MetricCard({
  label,
  value,
  basis,
  note,
  hint,
  empty = false,
  action,
}: MetricCardProps) {
  return (
    <section className={styles.card} aria-label={label}>
      <h3 className={styles.label}>{label}</h3>
      <p className={styles.value} data-empty={empty || undefined}>
        {value}
      </p>
      {basis ? <p className={styles.basis}>{basis}</p> : null}
      {note ? <p className={styles.basis}>{note}</p> : null}
      <p className={styles.hint}>{hint}</p>
      {action}
    </section>
  )
}
