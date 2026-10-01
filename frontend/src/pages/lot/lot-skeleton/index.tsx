import { clsx } from "clsx"
import type { ReactElement } from "react"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

const PRODUCT_ROWS = 6
const COMPANY_CARDS = 4
const EVIDENCE_ROWS = 3

function Bone({ className }: { readonly className?: string }) {
  return <span className={clsx(styles.bone, className)} />
}

function repeat(count: number, render: (index: number) => ReactElement) {
  return Array.from({ length: count }, (_, index) => render(index))
}

export function LotSkeleton({ label }: { readonly label: string }) {
  return (
    <div className={styles.skeleton} role="status" aria-busy="true">
      <VisuallyHidden>{label}</VisuallyHidden>
      <div className={styles.header} aria-hidden="true">
        <Bone className={styles.back} />
        <Bone className={styles.title} />
        <Bone className={styles.meta} />
      </div>
      <div className={styles.columns} aria-hidden="true">
        <div className={clsx(styles.panel, styles.products)}>
          <Bone className={styles.heading} />
          {repeat(PRODUCT_ROWS, (index) => (
            <span key={index} className={styles.row}>
              <Bone className={styles.line} />
              <Bone className={styles.short} />
            </span>
          ))}
        </div>
        <div className={clsx(styles.stack, styles.companies)}>
          <Bone className={styles.heading} />
          {repeat(COMPANY_CARDS, (index) => (
            <span key={index} className={styles.card}>
              <Bone className={styles.line} />
              <Bone className={styles.short} />
              <Bone />
            </span>
          ))}
        </div>
        <div className={styles.panel}>
          <Bone className={styles.hero} />
          {repeat(EVIDENCE_ROWS, (index) => (
            <span key={index} className={styles.row}>
              <Bone className={styles.line} />
              <Bone className={styles.short} />
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
