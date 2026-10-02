import { clsx } from "clsx"
import { type ReactNode, useId } from "react"
import { PaneFold, PaneFoldProvider, usePaneFold } from "@/shared/ui/pane-fold"
import styles from "./styles.module.css"

export type ResultSectionProps = {
  readonly title: string
  readonly aside?: ReactNode
  readonly framed?: boolean
  readonly children: ReactNode
}

export function ResultSection({ title, aside, framed = false, children }: ResultSectionProps) {
  const id = useId()
  const fold = usePaneFold()
  return (
    <section aria-labelledby={id} className={clsx(styles.section, framed && styles.framed)}>
      <div className={styles.heading}>
        <h2 id={id} tabIndex={-1} className={styles.title}>
          {title}
        </h2>
        {aside || fold ? (
          <span className={styles.aside}>
            {aside}
            {fold ? <PaneFold control={fold} /> : null}
          </span>
        ) : null}
      </div>
      <PaneFoldProvider value={null}>{children}</PaneFoldProvider>
    </section>
  )
}
