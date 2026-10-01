import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { PurchaseOutcome } from "@/entities/evidence/model"
import styles from "./styles.module.css"

export type PurchaseRowProps = {
  readonly title: string
  readonly outcome: PurchaseOutcome
  readonly lead?: string
  readonly href?: string
}

export function PurchaseRow({ title, outcome, lead, href }: PurchaseRowProps) {
  const { t } = useTranslation("evidence")
  return (
    <div className={styles.row}>
      {lead ? <span className={styles.lead}>{lead}</span> : null}
      <span
        className={clsx(styles.dot, outcome === "winner" ? styles.won : styles.took)}
        aria-hidden="true"
      />
      {href ? (
        <a href={href} className={styles.title}>
          {title}
        </a>
      ) : (
        <span className={styles.title}>{title}</span>
      )}
      <span className={styles.outcome}>{t(`outcome.${outcome}`)}</span>
    </div>
  )
}
