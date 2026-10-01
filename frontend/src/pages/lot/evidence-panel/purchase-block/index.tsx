import { useTranslation } from "react-i18next"
import { PurchaseRow } from "@/entities/evidence/ui/purchase-row"
import type { Company, Purchase } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Fold } from "@/shared/ui/fold"

export const PURCHASE_LIMIT = 3

function LotPurchase({ purchase }: { readonly purchase: Purchase }) {
  const { t } = useTranslation("lot")
  const title = purchase.lotId
    ? t("evidence.purchaseLot", { id: purchase.lotId, title: purchase.title })
    : purchase.title
  return (
    <PurchaseRow
      lead={purchase.year?.toString()}
      title={title}
      href={purchase.source?.url}
      outcome={purchase.outcome}
    />
  )
}
export function PurchaseBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  return (
    <Fold
      title={t("evidence.purchasesTitle")}
      aside={t("evidence.purchasesSummary", {
        count: company.similarPurchases,
        wins: company.wins,
      })}
    >
      {company.purchases.length > 0 ? (
        <CollapsibleList
          items={company.purchases}
          limit={PURCHASE_LIMIT}
          itemKey={(purchase) => `${purchase.lotId ?? ""}:${purchase.title}`}
          renderItem={(purchase) => <LotPurchase purchase={purchase} />}
        />
      ) : (
        <Caption>{t("evidence.noPurchases")}</Caption>
      )}
      <Caption>{t("evidence.purchasesNote")}</Caption>
    </Fold>
  )
}
