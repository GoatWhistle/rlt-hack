import { Children, type ReactNode } from "react"
import styles from "./styles.module.css"

export function FactRow({ children }: { readonly children: ReactNode }) {
  const facts = Children.toArray(children)
  return (
    <span className={styles.row}>
      {facts.flatMap((fact, index) => (index === 0 ? [fact] : [" ", fact]))}
    </span>
  )
}
