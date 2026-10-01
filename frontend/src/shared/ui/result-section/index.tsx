import { clsx } from "clsx"
import { type ReactNode, useId } from "react"
import styles from "./styles.module.css"

export type ResultSectionProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly framed?: boolean
  readonly children: ReactNode
}

export function ResultSection({ title, aside, framed = false, children }: ResultSectionProps) {
  const id = useId()
  return (
    <section aria-labelledby={id} className={clsx(styles.section, framed && styles.framed)}>
      <div className={styles.heading}>
        <h2 id={id} className={styles.title}>
          {title}
        </h2>
        {aside ? <span className={styles.aside}>{aside}</span> : null}
      </div>
      {children}
    </section>
  )
}
