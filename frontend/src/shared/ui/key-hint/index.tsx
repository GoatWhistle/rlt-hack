import { clsx } from "clsx"
import styles from "./styles.module.css"

export type KeyHintProps = {
  readonly keys: string
  readonly className?: string
}

export function KeyHint({ keys, className }: KeyHintProps) {
  return (
    <span className={clsx(styles.key, className)} aria-hidden="true">
      {keys}
    </span>
  )
}
