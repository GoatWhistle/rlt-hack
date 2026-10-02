import { useTranslation } from "react-i18next"
import { useParams } from "react-router"
import { usePurchaseSource } from "@/entities/recommendation/purchase-source"
import { lotPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Caption } from "@/shared/ui/caption"
import { ErrorState } from "@/shared/ui/error-state"
import { LoadingState } from "@/shared/ui/loading-state"
import { Stack } from "@/shared/ui/stack"
import { Tag } from "@/shared/ui/tag"
import styles from "./styles.module.css"

export function ProcurementSourcePage() {
  const { t } = useTranslation("lot")
  const { date } = useFormatters()
  const { uploadId = "", lotId = "", inn = "", purchaseId = "" } = useParams()
  const query = usePurchaseSource(uploadId, lotId, inn, purchaseId)
  const back = <BackLink to={lotPath(uploadId, lotId)}>{t("archive.back")}</BackLink>
  if (query.isPending) return <LoadingState label={t("archive.loading")} />
  if (query.isError)
    return (
      <ErrorState
        error={query.error}
        headingLevel={1}
        extraAction={back}
        onRetry={() => query.refetch()}
      />
    )
  const source = query.data
  return (
    <div className={styles.page}>
      {back}
      <article className={styles.record}>
        <header className={styles.header}>
          <p className={styles.eyebrow}>{t("archive.title")}</p>
          <h1 className={styles.title}>{source.title}</h1>
          <Tag tone={source.winner ? "success" : "tentative"}>
            {t(source.winner ? "evidence.outcome.winner" : "evidence.outcome.participant")}
          </Tag>
        </header>
        <dl className={styles.facts}>
          <div>
            <dt>{t("archive.published")}</dt>
            <dd>{date(source.date)}</dd>
          </div>
          <div>
            <dt>{t("archive.supplier")}</dt>
            <dd>{source.supplierInn}</dd>
          </div>
          <div>
            <dt>{t("archive.customer")}</dt>
            <dd>{source.customerInn || t("archive.unknown")}</dd>
          </div>
          <div>
            <dt>{t("archive.category")}</dt>
            <dd>{source.category}</dd>
          </div>
          <div>
            <dt>{t("archive.system")}</dt>
            <dd>{source.system || t("archive.unknown")}</dd>
          </div>
          <div>
            <dt>{t("archive.identifier")}</dt>
            <dd>{source.lotId}</dd>
          </div>
        </dl>
        <section className={styles.products} aria-label={t("archive.products")}>
          <h2>{t("archive.products")}</h2>
          {source.products.length ? (
            <Stack as="ul">
              {source.products.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </Stack>
          ) : (
            <Caption>{t("archive.noProducts")}</Caption>
          )}
        </section>
        <footer className={styles.footer}>
          <Caption>{t("grounds.scope")}</Caption>
        </footer>
      </article>
    </div>
  )
}
