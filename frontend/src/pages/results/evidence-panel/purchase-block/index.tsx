import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, Purchase } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Block } from "../block"
import { CollapsibleList } from "../collapsible-list"
import styles from "./styles.module.css"

export const PURCHASE_LIMIT = 3

function PurchaseRow({ purchase }: { readonly purchase: Purchase }) {
  const { t } = useTranslation()
  const winner = purchase.outcome === "winner"
  return (
    <div className={styles.row}>
      <span className={styles.year}>{purchase.year}</span>
      <span
        className={clsx(styles.dot, winner ? styles.won : styles.took)}
        aria-hidden="true"
      />
      {purchase.source ? (
        <a href={purchase.source.url} className={styles.title}>
          {purchase.title}
        </a>
      ) : (
        <span className={styles.title}>{purchase.title}</span>
      )}
      <span className={styles.outcome}>
        {t(`results.evidence.outcome.${purchase.outcome}`)}
      </span>
    </div>
  )
}

export function PurchaseBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation()
  return (
    <Block
      title={t("results.evidence.purchasesTitle")}
      aside={t("results.evidence.purchasesSummary", {
        count: company.similarPurchases,
        wins: company.wins,
      })}
    >
      {company.purchases.length > 0 ? (
        <CollapsibleList
          items={company.purchases}
          limit={PURCHASE_LIMIT}
          itemKey={(purchase) => purchase.title}
          renderItem={(purchase) => <PurchaseRow purchase={purchase} />}
        />
      ) : (
        <Caption>{t("results.evidence.noPurchases")}</Caption>
      )}
      <Caption>{t("results.evidence.purchasesNote")}</Caption>
    </Block>
  )
}
