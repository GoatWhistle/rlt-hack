import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type CaptionProps = {
  readonly muted?: boolean
  readonly children: ReactNode
}

export function Caption({ muted = false, children }: CaptionProps) {
  return <span className={clsx(styles.caption, muted && styles.muted)}>{children}</span>
}
