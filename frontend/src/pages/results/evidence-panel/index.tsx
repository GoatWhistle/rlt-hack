import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { ResultSection } from "../section"
import { ClarifyBlock } from "./clarify-block"
import { MatchBlock } from "./match-block"
import { PurchaseBlock } from "./purchase-block"
import styles from "./styles.module.css"
import { SummaryBlock } from "./summary-block"

export type EvidencePanelProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function EvidencePanel({ company, products }: EvidencePanelProps) {
  const { t } = useTranslation()
  return (
    <ResultSection title={t("results.evidence.title")}>
      <article className={styles.panel} aria-label={company.name}>
        <header className={styles.head}>
          <h2 className={styles.name}>{company.name}</h2>
          <Caption>
            {company.role} · {t("results.evidence.inn", { inn: company.inn })}
          </Caption>
        </header>
        <SummaryBlock company={company} />
        <MatchBlock company={company} products={products} />
        <PurchaseBlock company={company} />
        <ClarifyBlock items={company.clarify} />
      </article>
      <div className={styles.actions}>
        <Button>{t("results.evidence.shortlist")}</Button>
        <Button variant="secondary">{t("results.evidence.exclude")}</Button>
      </div>
    </ResultSection>
  )
}
