import { Link } from "react-router"
import { useFormatters } from "@/shared/i18n/formatters"
import { ProgressBar } from "@/shared/ui/progress-bar"
import styles from "./styles.module.css"

export type Bar = {
  readonly key: string
  readonly label: string
  readonly value: number
  readonly href?: string
}

export type BarListProps = {
  readonly bars: readonly Bar[]
  readonly total: number
}

export function BarList({ bars, total }: BarListProps) {
  const { number, percent } = useFormatters()
  return (
    <ul className={styles.list}>
      {bars.map((bar) => (
        <li key={bar.key} className={styles.item}>
          <span className={styles.label}>
            {bar.href ? (
              <Link to={bar.href} className={styles.link}>
                {bar.label}
              </Link>
            ) : (
              bar.label
            )}
          </span>
          <span className={styles.value}>
            {number(bar.value)}
            {total > 0 ? ` (${percent(bar.value / total)})` : ""}
          </span>
          <span className={styles.bar}>
            <ProgressBar
              role="meter"
              label={bar.label}
              value={bar.value}
              max={total}
              valueText={number(bar.value)}
            />
          </span>
        </li>
      ))}
    </ul>
  )
}
