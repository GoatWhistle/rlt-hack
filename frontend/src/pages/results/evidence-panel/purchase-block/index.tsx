import { useTranslation } from "react-i18next"
import type { Company, Purchase } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Tag } from "@/shared/ui/tag"
import { Block } from "../block"
import { CollapsibleList } from "../collapsible-list"
import { FactRow } from "../fact-row"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

export const PURCHASE_LIMIT = 2

function PurchaseRow({ purchase }: { readonly purchase: Purchase }) {
  const { t } = useTranslation()
  return (
    <FactRow
      title={purchase.title}
      tag={
        <Tag tone={purchase.outcome === "winner" ? "solid" : "tentative"}>
          {t(`results.evidence.outcome.${purchase.outcome}`)} · {purchase.year}
        </Tag>
      }
    >
      <SourceLine source={purchase.source} />
    </FactRow>
  )
}

export function PurchaseBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation()
  return (
    <Block title={t("results.evidence.purchasesTitle")} icon="checkCircle" tone="current">
      <p className={styles.total}>
        {t("results.evidence.purchasesSummary", {
          count: company.similarPurchases,
          wins: company.wins,
        })}
      </p>
      {company.purchases.length > 0 ? (
        <CollapsibleList
          items={company.purchases}
          limit={PURCHASE_LIMIT}
          itemKey={(purchase) => purchase.title}
          renderItem={(purchase) => <PurchaseRow purchase={purchase} />}
        />
      ) : (
        <Caption muted>{t("results.evidence.noPurchases")}</Caption>
      )}
      <Caption muted>{t("results.evidence.purchasesNote")}</Caption>
    </Block>
  )
}
