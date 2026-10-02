import { clsx } from "clsx"
import { Children, type ReactNode } from "react"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type MetaChipTone = "neutral" | "accent" | "warning" | "muted"

const TONES: Record<MetaChipTone, string | undefined> = {
  neutral: undefined,
  accent: styles.accent,
  warning: styles.warning,
  muted: styles.muted,
}

export type MetaChipProps = {
  readonly children: ReactNode
  readonly tone?: MetaChipTone
  readonly icon?: IconName
}

export function MetaChip({ children, tone = "neutral", icon }: MetaChipProps) {
  return (
    <span className={clsx(styles.chip, TONES[tone])}>
      {icon ? <Icon name={icon} size="sm" /> : null}
      <span>{children}</span>
    </span>
  )
}

export function MetaChips({ children }: { readonly children: ReactNode }) {
  const chips = Children.toArray(children)
  return (
    <span className={styles.chips}>
      {chips.flatMap((chip, index) => (index === 0 ? [chip] : [" ", chip]))}
    </span>
  )
}
