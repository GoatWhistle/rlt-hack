import { useTranslation } from "react-i18next"
import { EvidenceAction, EvidenceFrame } from "@/entities/evidence/ui/evidence-frame"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { ClarifyBlock } from "./clarify-block"
import { Confirmations } from "./confirmations"
import { Hero } from "./hero"
import { HistoryBlock } from "./history-block"
import { MatchBlock } from "./match-block"
import { ProcurementEvidence } from "./procurement-evidence"
import { PurchaseBlock } from "./purchase-block"

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
    <EvidenceFrame
      label={company.name}
      swapKey={company.id}
      actions={
        <>
          <EvidenceAction
            variant={chosen ? "secondary" : "strong"}
            icon={chosen ? <Icon name="check" /> : undefined}
            label={chosen ? t("evidence.chosen") : t("evidence.choose")}
            onClick={onChoose}
          />
          <EvidenceAction
            variant="secondary"
            label={t("evidence.profile")}
            onClick={onProfile}
          />
        </>
      }
    >
      <Hero company={company} products={products} />
      {company.purchases.length > 0 && company.history ? (
        <>
          <ProcurementEvidence company={company} />
          <HistoryBlock company={company} showExamples={false} />
        </>
      ) : company.history ? (
        <HistoryBlock company={company} />
      ) : null}
      {products.length > 0 ? <Confirmations company={company} products={products} /> : null}
      {products.length > 0 ? <MatchBlock company={company} products={products} /> : null}
      {!company.history ? <PurchaseBlock company={company} /> : null}
      <ClarifyBlock items={company.clarify} />
    </EvidenceFrame>
  )
}
