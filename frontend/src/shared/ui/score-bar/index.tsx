import styles from "./styles.module.css"

export type ScoreBarProps = {
  readonly value: number
  readonly label: string
  readonly valueText: string
  readonly showLabel?: boolean
}

export function ScoreBar({ value, label, valueText, showLabel = false }: ScoreBarProps) {
  const share = Math.min(1, Math.max(0, value))
  return (
    <span className={styles.score}>
      {showLabel ? (
        <span className={styles.label} aria-hidden="true">
          {label}
        </span>
      ) : null}
      <meter
        className={styles.track}
        min={0}
        max={1}
        value={share}
        aria-label={label}
        aria-valuetext={valueText}
      />
    </span>
  )
}
