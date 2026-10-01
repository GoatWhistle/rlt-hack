import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type EmptyStateProps = {
  readonly title: string
  readonly description?: string
  readonly details?: string
  readonly actions?: ReactNode
  readonly headingLevel?: 1 | 2
  readonly tone?: "neutral" | "error"
}

export function EmptyState({
  title,
  description,
  details,
  actions,
  headingLevel = 1,
  tone = "neutral",
}: EmptyStateProps) {
  const Heading = headingLevel === 1 ? "h1" : "h2"
  return (
    <section className={styles.state} role={tone === "error" ? "alert" : undefined}>
      <Heading className={styles.title}>{title}</Heading>
      {description ? <p className={styles.description}>{description}</p> : null}
      {details ? <p className={styles.details}>{details}</p> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </section>
  )
}
