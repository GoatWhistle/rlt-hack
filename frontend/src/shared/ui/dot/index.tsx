import { clsx } from "clsx"
import styles from "./styles.module.css"

export type DotShape = "filled" | "hollow" | "dashed"
export type DotTone = "accent" | "warning" | "muted" | "current"
export type DotSize = "sm" | "md"

const SHAPES: Record<DotShape, string | undefined> = {
  filled: styles.filled,
  hollow: styles.hollow,
  dashed: styles.dashed,
}

const TONES: Record<DotTone, string | undefined> = {
  accent: styles.accent,
  warning: styles.warning,
  muted: styles.muted,
  current: undefined,
}

export type DotProps = {
  readonly shape: DotShape
  readonly tone?: DotTone
  readonly size?: DotSize
}

export function Dot({ shape, tone = "current", size = "sm" }: DotProps) {
  return (
    <span
      aria-hidden="true"
      className={clsx(styles.dot, SHAPES[shape], TONES[tone], size === "md" && styles.md)}
    />
  )
}
