import { useTranslation } from "react-i18next"
import { Link, useSearchParams } from "react-router"
import { useRecords } from "@/entities/analytics/queries"
import {
  RECORDS_PAGE_SIZE,
  readOffset,
  readProblem,
  writeFilters,
} from "@/entities/analytics/scope"
import { ANALYTICS_PATH, ANALYTICS_RECORDS_PATH } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { DataCell, type DataColumn, DataTable } from "@/shared/ui/data-table"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { useScope } from "../use-scope"
import styles from "./styles.module.css"

export function RecordsPage() {
  const { t } = useTranslation("analytics")
  const { money, dateTime } = useFormatters()
  const scope = useScope()
  const [params] = useSearchParams()
  const problem = readProblem(params)
  const category = params.get("category") || undefined
  const offset = readOffset(params)
  const query = useRecords(scope.filters, {
    problem,
    category,
    offset,
    limit: RECORDS_PAGE_SIZE,
  })
  if (query.isPending) {
    return <PageSkeleton label={t("state.loading")} rows={4} />
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const page = query.data
  const columns: DataColumn[] = [
    { key: "name", label: t("records.columns.name") },
    { key: "source", label: t("records.columns.source") },
    { key: "company", label: t("records.columns.company") },
    { key: "category", label: t("records.columns.category") },
    { key: "price", label: t("records.columns.price"), numeric: true },
    { key: "seen", label: t("records.columns.seen") },
  ]
  const hrefFor = (target: number) => {
    const next = new URLSearchParams(params)
    if (target > 1) next.set("page", String(target))
    else next.delete("page")
    return `${ANALYTICS_RECORDS_PATH}${writeFilters(scope.filters, next)}`
  }
  const current = offset / RECORDS_PAGE_SIZE + 1
  const last = Math.max(1, Math.ceil(page.total / RECORDS_PAGE_SIZE))
  const what = [
    problem ? t(`records.problem.${problem}`) : null,
    category ? t("records.category", { code: category }) : null,
  ].filter((part): part is string => part !== null)
  return (
    <section className={styles.page}>
      <header className={styles.head}>
        <h2 className={styles.title}>{t("records.title")}</h2>
        <p className={styles.note}>{t("records.description")}</p>
        {what.length > 0 ? (
          <p className={styles.note}>{t("records.filteredBy", { what: what.join(", ") })}</p>
        ) : null}
        <Link to={`${ANALYTICS_PATH}${scope.search}`} className={styles.link}>
          {t("records.back")}
        </Link>
      </header>
      {page.changedAfter > 0 ? (
        <p className={styles.warning} role="status">
          {t("records.changed", { count: page.changedAfter })}
        </p>
      ) : null}
      {page.items.length === 0 ? (
        <EmptyState headingLevel={2} title={t("records.empty")} />
      ) : (
        <DataTable label={t("records.title")} columns={columns}>
          {page.items.map((item) => (
            <tr key={item.offerId}>
              <DataCell>
                <a href={item.url} className={styles.link} target="_blank" rel="noreferrer">
                  {item.name}
                </a>
              </DataCell>
              <DataCell>{item.sourceName}</DataCell>
              <DataCell>{item.supplierName || t("records.noValue")}</DataCell>
              <DataCell>{item.okpd2Code || t("records.noValue")}</DataCell>
              <DataCell numeric>
                {item.price === undefined
                  ? t("records.noValue")
                  : money(item.price, item.currency || "RUB")}
              </DataCell>
              <DataCell>{dateTime(item.lastSeenAt)}</DataCell>
            </tr>
          ))}
        </DataTable>
      )}
      <nav className={styles.pager} aria-label={t("records.pages")}>
        <span>
          {t("records.range", {
            from: page.total === 0 ? 0 : offset + 1,
            to: Math.min(page.total, offset + RECORDS_PAGE_SIZE),
            total: page.total,
          })}
        </span>
        {current > 1 ? <Link to={hrefFor(current - 1)}>{t("records.previous")}</Link> : null}
        {current < last ? <Link to={hrefFor(current + 1)}>{t("records.next")}</Link> : null}
      </nav>
    </section>
  )
}
