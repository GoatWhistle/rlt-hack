import type { ReactNode } from "react"
import { Button, type ButtonVariant } from "@/shared/ui/button"
import styles from "./styles.module.css"

export type EvidenceFrameProps = {
  readonly label: string
  readonly swapKey: string
  readonly actions: ReactNode
  readonly children: ReactNode
}

export function EvidenceFrame({ label, swapKey, actions, children }: EvidenceFrameProps) {
  return (
    <article className={styles.panel} aria-label={label}>
      <div key={swapKey} className={styles.content}>
        {children}
      </div>
      <div className={styles.actions} data-dock="">
        {actions}
      </div>
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
      {icon ? <span className={styles.icon}>{icon}</span> : null}
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
