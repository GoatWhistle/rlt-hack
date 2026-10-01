import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, Purchase } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Fold } from "../fold"
import styles from "./styles.module.css"

export const PURCHASE_LIMIT = 3

function PurchaseRow({ purchase }: { readonly purchase: Purchase }) {
  const { t } = useTranslation("lot")
  const winner = purchase.outcome === "winner"
  const title = purchase.lotId
    ? t("evidence.purchaseLot", { id: purchase.lotId, title: purchase.title })
    : purchase.title
  return (
    <div className={styles.row}>
      <span className={styles.year}>{purchase.year}</span>
      <span
        className={clsx(styles.dot, winner ? styles.won : styles.took)}
        aria-hidden="true"
      />
      {purchase.source ? (
        <a href={purchase.source.url} className={styles.title}>
          {title}
        </a>
      ) : (
        <span className={styles.title}>{title}</span>
      )}
      <span className={styles.outcome}>{t(`evidence.outcome.${purchase.outcome}`)}</span>
    </div>
  )
}

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
          itemKey={(purchase) => `${purchase.lotId ?? ""}:${purchase.title}`}
          renderItem={(purchase) => <PurchaseRow purchase={purchase} />}
        />
      ) : (
        <Caption>{t("evidence.noPurchases")}</Caption>
      )}
      <Caption>{t("evidence.purchasesNote")}</Caption>
    </Fold>
  )
}
