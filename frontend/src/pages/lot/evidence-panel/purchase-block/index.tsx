import { useTranslation } from "react-i18next"
import { PurchaseRow } from "@/entities/evidence/ui/purchase-row"
import type { Company } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Fold } from "@/shared/ui/fold"

export const PURCHASE_LIMIT = 3

export function PurchaseBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  return (
    <Fold
      title={t("evidence.purchasesTitle")}
      aside={
        company.similarPurchases === null || company.wins === null
          ? t("compare.unknown")
          : t("evidence.purchasesSummary", {
              count: company.similarPurchases,
              wins: company.wins,
            })
      }
    >
      {company.purchases.length > 0 ? (
        <CollapsibleList
          items={company.purchases}
          limit={PURCHASE_LIMIT}
          itemKey={(purchase) => purchase.title}
          renderItem={(purchase) => (
            <PurchaseRow
              title={purchase.title}
              outcome={purchase.outcome}
              lead={String(purchase.year)}
              href={purchase.source?.url}
            />
          )}
        />
      ) : (
        <Caption>{t("evidence.noPurchases")}</Caption>
      )}
      <Caption>{t("evidence.purchasesNote")}</Caption>
    </Fold>
  )
}
