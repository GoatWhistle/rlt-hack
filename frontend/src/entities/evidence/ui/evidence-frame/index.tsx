import type { ReactNode } from "react"
import { Button, type ButtonVariant } from "@/shared/ui/button"
import styles from "./styles.module.css"

export type EvidenceFrameProps = {
  readonly label: string
  readonly actions: ReactNode
  readonly children: ReactNode
}

export function EvidenceFrame({ label, actions, children }: EvidenceFrameProps) {
  return (
    <article className={styles.panel} aria-label={label}>
      {children}
      <div className={styles.actions}>{actions}</div>
    </article>
  )
}

export type EvidenceActionProps = {
  readonly variant: ButtonVariant
  readonly label: string
  readonly shortLabel?: string
  readonly icon?: ReactNode
  readonly onClick: () => void
}

export function EvidenceAction({
  variant,
  label,
  shortLabel,
  icon,
  onClick,
}: EvidenceActionProps) {
  return (
    <Button
      variant={variant}
      className={styles.action}
      aria-label={shortLabel ? label : undefined}
      onClick={onClick}
    >
      {icon}
      {shortLabel ? (
        <>
          <span className={styles.full}>{label}</span>
          <span className={styles.short}>{shortLabel}</span>
        </>
      ) : (
        label
      )}
    </Button>
  )
}
