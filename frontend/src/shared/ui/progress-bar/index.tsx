import styles from "./styles.module.css"

export type ProgressBarProps = {
  readonly label: string
  readonly value: number
  readonly max: number
}

export function ProgressBar({ label, value, max }: ProgressBarProps) {
  const share = max > 0 ? Math.min(1, value / max) : 0
  return (
    <span
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className={styles.track}
    >
      <span className={styles.fill} style={{ transform: `scaleX(${share})` }} />
    </span>
  )
}
