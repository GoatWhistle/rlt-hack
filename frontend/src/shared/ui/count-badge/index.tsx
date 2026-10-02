import { clsx } from "clsx"
import { useFormatters } from "@/shared/i18n/formatters"
import styles from "./styles.module.css"

export type CountBadgeProps = {
  readonly value: number
  readonly corner?: boolean
}

export function CountBadge({ value, corner = false }: CountBadgeProps) {
  const { number } = useFormatters()
  return (
    <span key={value} className={clsx(styles.count, corner && styles.corner)}>
      {number(value)}
    </span>
  )
}
