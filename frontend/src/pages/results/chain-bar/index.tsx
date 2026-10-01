import { clsx } from "clsx"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { Company, Recommendation } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import styles from "./styles.module.css"

export type ChainBarProps = {
  readonly recommendation: Recommendation
  readonly selected: Company
}

type StepProps = {
  readonly label: string
  readonly value: string
  readonly note: ReactNode
  readonly active?: boolean
}

function Step({ label, value, note, active = false }: StepProps) {
  return (
    <li className={clsx(styles.step, active && styles.active)}>
      <Caption muted={!active}>{label}</Caption>
      <span className={styles.value}>{value}</span>
      <span className={styles.note}>{note}</span>
    </li>
  )
}

export function ChainBar({ recommendation, selected }: ChainBarProps) {
  const { t } = useTranslation()
  const { products, companies } = recommendation
  const origins = (origin: string) => products.filter((p) => p.origin === origin).length
  const recommended = companies.filter((c) => c.status === "recommended").length
  return (
    <ol className={styles.chain} aria-label={t("results.chain.label")}>
      <Step
        label={t("results.chain.request")}
        value={recommendation.requestTitle}
        note={t("results.chain.lotFromFile", { lot: recommendation.lotLabel })}
      />
      <Step
        label={t("results.chain.products")}
        value={t("results.chain.productCount", { count: products.length })}
        note={t("results.chain.originSummary", {
          notice: origins("notice"),
          inferred: origins("inferred"),
          user: origins("user"),
        })}
      />
      <Step
        label={t("results.chain.companies")}
        value={t("results.chain.companyCount", { count: companies.length })}
        note={t("results.chain.statusSummary", {
          recommended,
          check: companies.length - recommended,
        })}
      />
      <Step
        active
        label={t("results.chain.evidence")}
        value={selected.name}
        note={t("results.chain.evidenceSummary", {
          count: selected.evidence.length,
          clarify: selected.clarify.length,
        })}
      />
    </ol>
  )
}
