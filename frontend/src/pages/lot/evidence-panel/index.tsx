import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { ClarifyBlock } from "./clarify-block"
import { Confirmations } from "./confirmations"
import { Hero } from "./hero"
import { HistoryBlock } from "./history-block"
import { MatchBlock } from "./match-block"
import { PurchaseBlock } from "./purchase-block"
import styles from "./styles.module.css"

export type EvidencePanelProps = {
  readonly company: Company
  readonly products: readonly Product[]
  readonly chosen: boolean
  readonly onChoose: () => void
  readonly onProfile: () => void
}

export function EvidencePanel({
  company,
  products,
  chosen,
  onChoose,
  onProfile,
}: EvidencePanelProps) {
  const { t } = useTranslation("lot")
  return (
    <article className={styles.panel} aria-label={company.name}>
      <Hero company={company} products={products} />
      {company.history ? <HistoryBlock company={company} /> : null}
      {products.length > 0 ? <Confirmations company={company} products={products} /> : null}
      {products.length > 0 ? <MatchBlock company={company} products={products} /> : null}
      {!company.history || company.purchases.length > 0 ? (
        <PurchaseBlock company={company} />
      ) : null}
      <ClarifyBlock items={company.clarify} />
      <div className={styles.actions}>
        <Button
          variant={chosen ? "secondary" : "primary"}
          className={styles.action}
          onClick={onChoose}
        >
          {chosen ? <Icon name="check" /> : null}
          {chosen ? t("evidence.chosen") : t("evidence.choose")}
        </Button>
        <Button
          variant="secondary"
          className={styles.action}
          aria-label={t("evidence.profile")}
          onClick={onProfile}
        >
          <span className={styles.full}>{t("evidence.profile")}</span>
          <span className={styles.short}>{t("evidence.profileShort")}</span>
        </Button>
      </div>
    </article>
  )
}
