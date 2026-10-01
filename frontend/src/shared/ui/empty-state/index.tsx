import { clsx } from "clsx"
import type { ReactNode } from "react"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type EmptyStateProps = {
  readonly title: string
  readonly description?: string
  readonly details?: string
  readonly actions?: ReactNode
  readonly headingLevel?: 1 | 2
  readonly tone?: "neutral" | "error"
  readonly icon?: IconName
}

export function EmptyState({
  title,
  description,
  details,
  actions,
  headingLevel = 1,
  tone = "neutral",
  icon,
}: EmptyStateProps) {
  const Heading = headingLevel === 1 ? "h1" : "h2"
  const error = tone === "error"
  const shown = icon ?? (error ? "warning" : undefined)
  return (
    <section
      className={clsx(styles.state, headingLevel === 1 && styles.page)}
      role={error ? "alert" : undefined}
    >
      {shown ? (
        <span className={clsx(styles.badge, error && styles.error)}>
          <Icon name={shown} size="lg" />
        </span>
      ) : null}
      <Heading className={styles.title}>{title}</Heading>
      {description ? <p className={styles.description}>{description}</p> : null}
      {details ? <p className={styles.details}>{details}</p> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </section>
  )
}
