import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type StackGap = "tight" | "normal" | "wide"

const GAPS: Record<StackGap, string | undefined> = {
  tight: styles.tight,
  normal: styles.normal,
  wide: styles.wide,
}

export type StackProps = {
  readonly gap?: StackGap
  readonly as?: "div" | "li" | "ul"
  readonly children: ReactNode
}

export function Stack({ gap = "normal", as: Element = "div", children }: StackProps) {
  return (
    <Element className={clsx(styles.stack, GAPS[gap], Element === "ul" && styles.list)}>
      {children}
    </Element>
  )
}
