import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type TagTone = "solid" | "tentative" | "accent" | "warning" | "success" | "danger"

const TONES: Record<TagTone, string | undefined> = {
  solid: undefined,
  tentative: styles.tentative,
  accent: styles.accent,
  warning: styles.warning,
  success: styles.success,
  danger: styles.danger,
}

export type TagProps = {
  readonly tone?: TagTone
  readonly as?: "span" | "li"
  readonly wrap?: boolean
  readonly children: ReactNode
}

export function Tag({
  tone = "solid",
  as: Element = "span",
  wrap = false,
  children,
}: TagProps) {
  return (
    <Element className={clsx(styles.tag, TONES[tone], wrap && styles.wrap)}>{children}</Element>
  )
}
