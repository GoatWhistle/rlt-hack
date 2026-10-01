import { clsx } from "clsx"
import type { HTMLAttributes } from "react"
import styles from "./styles.module.css"

export type VisuallyHiddenProps = HTMLAttributes<HTMLElement> & {
  readonly as?: "span" | "legend" | "h2"
}

export function VisuallyHidden({
  as: Element = "span",
  className,
  ...props
}: VisuallyHiddenProps) {
  return <Element className={clsx(styles.hidden, className)} {...props} />
}
