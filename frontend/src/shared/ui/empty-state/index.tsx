import { clsx } from "clsx"
import type { ReactNode } from "react"
import { Icon, type IconName } from "@/shared/ui/icon"
import { PageTitle } from "@/shared/ui/page-title"
import styles from "./styles.module.css"

export type EmptyStateProps = {
  readonly title: string
  readonly description?: string
  readonly details?: string
  readonly actions?: ReactNode
  readonly headingLevel?: 1 | 2
  readonly tone?: "neutral" | "error"
  readonly icon?: IconName
  readonly children?: ReactNode
}

export function EmptyState({
  title,
  description,
  details,
  actions,
  headingLevel = 1,
  tone = "neutral",
  icon,
  children,
}: EmptyStateProps) {
  const page = headingLevel === 1
  const error = tone === "error"
  const shown = icon ?? (error ? "warning" : undefined)
  return (
    <section
      className={clsx(styles.state, page && styles.page)}
      role={error ? "alert" : undefined}
    >
      {shown ? (
        <span className={clsx(styles.badge, error && styles.error)}>
          <Icon name={shown} size="lg" />
        </span>
      ) : null}
      {page ? (
        <PageTitle size="record" className={styles.heading}>
          {title}
        </PageTitle>
      ) : (
        <h2 className={clsx(styles.heading, styles.title)}>{title}</h2>
      )}
      {description ? <p className={styles.description}>{description}</p> : null}
      {details ? <p className={styles.details}>{details}</p> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
      {children}
    </section>
  )
}
