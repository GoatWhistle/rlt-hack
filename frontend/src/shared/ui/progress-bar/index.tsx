import styles from "./styles.module.css"

export type ProgressBarProps = {
  readonly label: string
  readonly value: number
  readonly max: number
  readonly valueText?: string
  readonly role?: "progressbar" | "meter"
}

export function ProgressBar({
  label,
  value,
  max,
  valueText,
  role = "progressbar",
}: ProgressBarProps) {
  const share = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0
  return (
    // biome-ignore lint/a11y/useAriaPropsSupportedByRole: role is progressbar or meter, both take a label and values
    <span
      role={role}
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-valuetext={valueText}
      className={styles.track}
    >
      <span className={styles.fill} style={{ transform: `scaleX(${share})` }} />
    </span>
  )
}
