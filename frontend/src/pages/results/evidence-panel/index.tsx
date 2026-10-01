import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Button } from "@/shared/ui/button"
import { ClarifyBlock } from "./clarify-block"
import { Hero } from "./hero"
import { MatchBlock } from "./match-block"
import { PurchaseBlock } from "./purchase-block"
import styles from "./styles.module.css"

export type EvidencePanelProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function EvidencePanel({ company, products }: EvidencePanelProps) {
  const { t } = useTranslation()
  return (
    <article className={styles.panel} aria-label={company.name}>
      <Hero company={company} products={products} />
      <MatchBlock company={company} products={products} />
      <PurchaseBlock company={company} />
      <ClarifyBlock items={company.clarify} />
      <div className={styles.actions}>
        <Button variant="strong">{t("results.evidence.shortlist")}</Button>
        <Button variant="secondary">{t("results.evidence.exclude")}</Button>
      </div>
    </article>
  )
}
