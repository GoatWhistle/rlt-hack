import { type ReactNode, useId } from "react"
import styles from "./styles.module.css"

export type ResultSectionProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly children: ReactNode
}

export function ResultSection({ title, aside, children }: ResultSectionProps) {
  const id = useId()
  return (
    <section aria-labelledby={id} className={styles.section}>
      <div className={styles.heading}>
        <h2 id={id} className={styles.title}>
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  )
}
