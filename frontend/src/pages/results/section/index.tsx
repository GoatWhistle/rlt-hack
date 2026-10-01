import { clsx } from "clsx"
import { type ReactNode, useId } from "react"
import styles from "./styles.module.css"

export type ColumnWidth = "narrow" | "medium" | "wide"

const WIDTHS: Record<ColumnWidth, string | undefined> = {
  narrow: styles.narrow,
  medium: styles.medium,
  wide: styles.wide,
}

export type ResultSectionProps = {
  readonly title: string
  readonly width: ColumnWidth
  readonly children: ReactNode
}

export function ResultSection({ title, width, children }: ResultSectionProps) {
  const id = useId()
  return (
    <section aria-labelledby={id} className={clsx(styles.section, WIDTHS[width])}>
      <h2 id={id} className={styles.title}>
        {title}
      </h2>
      {children}
    </section>
  )
}
