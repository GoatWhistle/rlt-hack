import { ProgressBar } from "@/shared/ui/progress-bar"
import styles from "./styles.module.css"

export type ScoreBarProps = {
  readonly value: number
  readonly label: string
  readonly valueText: string
  readonly showLabel?: boolean
}

export function ScoreBar({ value, label, valueText, showLabel = false }: ScoreBarProps) {
  return (
    <span className={styles.score}>
      {showLabel ? (
        <span className={styles.label} aria-hidden="true">
          {label}
        </span>
      ) : null}
      <span className={styles.bar}>
        <ProgressBar
          role="meter"
          label={label}
          value={Math.min(1, Math.max(0, value))}
          max={1}
          valueText={valueText}
        />
      </span>
    </span>
  )
}
