import { Fragment, type ReactNode } from "react"
import styles from "./styles.module.css"

export type Fact = {
  readonly key: string
  readonly term: string
  readonly value: ReactNode
  readonly mono?: boolean
}

export function FactList({ facts }: { readonly facts: readonly Fact[] }) {
  return (
    <dl className={styles.facts}>
      {facts.map((fact) => (
        <Fragment key={fact.key}>
          <dt>{fact.term}</dt>
          <dd className={fact.mono ? styles.mono : undefined}>{fact.value}</dd>
        </Fragment>
      ))}
    </dl>
  )
}
