import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type TruncateProps = {
  readonly className?: string
  readonly children: ReactNode
}

export function Truncate({ className, children }: TruncateProps) {
  return <span className={clsx(styles.truncate, className)}>{children}</span>
}
