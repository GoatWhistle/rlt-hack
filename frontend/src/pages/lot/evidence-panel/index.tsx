import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { CandidatePagerProps } from "@/entities/evidence/ui/candidate-pager"
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
  readonly pager?: CandidatePagerProps
  readonly extraAction?: ReactNode
  readonly onChoose: () => void
  readonly onProfile: () => void
}

export function EvidencePanel({
  company,
  products,
  chosen,
  pager,
  extraAction,
  onChoose,
  onProfile,
}: EvidencePanelProps) {
  const { t } = useTranslation("lot")
  const { t: candidate } = useTranslation("candidate")
  return (
    <EvidenceFrame
      label={company.name}
      extra={extraAction}
      swapKey={company.id}
      actions={
        <>
          <EvidenceAction
            variant={chosen ? "secondary" : "primary"}
            icon={chosen ? <Icon name="check" /> : undefined}
            label={chosen ? t("evidence.chosen") : t("evidence.choose")}
            onClick={onChoose}
          />
          <EvidenceAction
            variant="secondary"
            label={t("evidence.profile")}
            shortLabel={candidate("panel.profileShort")}
            onClick={onProfile}
          />
        </>
      }
    >
      <Hero company={company} products={products} pager={pager} />
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
