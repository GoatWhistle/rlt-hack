import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import { Tag } from "@/shared/ui/tag"
import { Block } from "../block"
import styles from "./styles.module.css"

export function ProcurementEvidence({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  return (
    <Block title={t("grounds.title")}>
      <dl className={styles.metrics}>
        <div>
          <dt>{t("grounds.categoryLots")}</dt>
          <dd>{company.similarPurchases}</dd>
        </div>
        <div>
          <dt>{t("grounds.wins")}</dt>
          <dd>{company.wins}</dd>
        </div>
        <div>
          <dt>{t("grounds.category")}</dt>
          <dd>{company.history?.category}</dd>
        </div>
      </dl>
      <p className={styles.explanation}>{t("grounds.reason")}</p>
      <CollapsibleList
        items={company.purchases}
        limit={3}
        itemKey={(purchase) => purchase.source?.url ?? purchase.title}
        renderItem={(purchase) => (
          <article className={styles.purchase}>
            <div className={styles.meta}>
              <time>{purchase.date ?? purchase.year}</time>
              <Tag tone={purchase.outcome === "winner" ? "success" : "tentative"}>
                {t(`evidence.outcome.${purchase.outcome}`)}
              </Tag>
            </div>
            <h4 className={styles.title}>{purchase.title}</h4>
            {purchase.products?.length ? (
              <ul className={styles.products}>
                {purchase.products.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            ) : null}
            {purchase.customerInn ? (
              <Caption>{t("grounds.customer", { inn: purchase.customerInn })}</Caption>
            ) : null}
            {purchase.source ? (
              <a
                className={styles.link}
                href={purchase.source.url}
                target="_blank"
                rel="noreferrer"
              >
                {t("grounds.openSource")}
              </a>
            ) : null}
          </article>
        )}
      />
      <Caption>{t("grounds.scope")}</Caption>
    </Block>
  )
}
