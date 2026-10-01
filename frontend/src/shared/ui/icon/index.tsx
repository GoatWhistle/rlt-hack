import { clsx } from "clsx"
import { ICON_PATHS, type IconName } from "./paths"

export type { IconName }

import styles from "./styles.module.css"

export type IconSize = "sm" | "md" | "lg"
export type IconTone = "current" | "confirmed" | "source"

const SIZES: Record<IconSize, string | undefined> = {
  sm: styles.sm,
  md: styles.md,
  lg: styles.lg,
}

const TONES: Record<IconTone, string | undefined> = {
  current: undefined,
  confirmed: styles.confirmed,
  source: styles.source,
}

export type IconProps = {
  readonly name: IconName
  readonly size?: IconSize
  readonly tone?: IconTone
  readonly label?: string
}

export function Icon({ name, size = "md", tone = "current", label }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={clsx(styles.icon, SIZES[size], TONES[tone])}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      {ICON_PATHS[name].map((path) => (
        <path key={path} d={path} />
      ))}
    </svg>
  )
}
