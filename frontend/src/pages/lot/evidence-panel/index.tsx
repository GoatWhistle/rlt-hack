import { useTranslation } from "react-i18next"
import { EvidenceAction, EvidenceFrame } from "@/entities/evidence/ui/evidence-frame"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { useClarifyItems } from "../status"
import { ClarifyBlock } from "./clarify-block"
import { Confirmations } from "./confirmations"
import { Hero } from "./hero"
import { MatchBlock } from "./match-block"
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
  const clarifyItems = useClarifyItems()
  return (
    <EvidenceFrame
      label={company.name}
      actions={
        <>
          <EvidenceAction
            variant={chosen ? "secondary" : "primary"}
            icon={chosen ? <Icon name="check" /> : null}
            label={chosen ? t("evidence.chosen") : t("evidence.choose")}
            onClick={onChoose}
          />
          <EvidenceAction
            variant="secondary"
            label={t("evidence.profile")}
            shortLabel={t("evidence.profileShort")}
            onClick={onProfile}
          />
        </>
      }
    >
      <Hero company={company} products={products} />
      {products.length > 0 ? <Confirmations company={company} products={products} /> : null}
      {products.length > 0 ? <MatchBlock company={company} products={products} /> : null}
      <PurchaseBlock company={company} />
      <ClarifyBlock items={clarifyItems(company, products)} />
    </EvidenceFrame>
  )
}
