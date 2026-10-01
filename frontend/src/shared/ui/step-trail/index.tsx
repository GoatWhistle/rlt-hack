import { clsx } from "clsx"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type StepTrailProps = {
  readonly label: string
  readonly steps: readonly string[]
  readonly current: number
}

export function StepTrail({ label, steps, current }: StepTrailProps) {
  return (
    <ol className={styles.chain} aria-label={label}>
      {steps.map((step, index) => {
        const done = index < current
        const active = index === current
        return (
          <li
            key={step}
            className={clsx(styles.step, active && styles.current)}
            aria-current={active ? "step" : undefined}
          >
            {done ? (
              <span className={styles.done}>
                <Icon name="check" size="sm" />
              </span>
            ) : (
              <span
                className={clsx(styles.marker, !active && styles.pending)}
                aria-hidden="true"
              />
            )}
            {step}
            {index < steps.length - 1 ? (
              <span className={styles.link} aria-hidden="true" />
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
