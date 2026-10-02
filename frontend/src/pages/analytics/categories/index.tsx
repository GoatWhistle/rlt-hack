import { useTranslation } from "react-i18next"
import { Link, useParams } from "react-router"
import type { Category } from "@/entities/analytics/model"
import { useCategories } from "@/entities/analytics/queries"
import { recordsHref, writeFilters } from "@/entities/analytics/scope"
import { ANALYTICS_CATEGORIES_PATH, analyticsCategoryPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { DataCell, type DataColumn, DataTable } from "@/shared/ui/data-table"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { PanelBlock } from "@/shared/ui/panel-block"
import { QuietLink } from "@/shared/ui/quiet-link"
import { Reveal } from "@/shared/ui/reveal"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { Stack } from "@/shared/ui/stack"
import { BarList } from "../bar-list"
import { RatioCell } from "../ratio-figure"
import { SnapshotBar } from "../snapshot-bar"
import { useScope } from "../use-scope"
import styles from "./styles.module.css"

const ORIGINS = ["system", "source", "absent"] as const

export function CategoriesPage() {
  const { t } = useTranslation("analytics")
  const { number } = useFormatters()
  const { code = "" } = useParams()
  const scope = useScope()
  const query = useCategories(scope.filters)
  if (query.isPending) {
    return <PageSkeleton label={t("state.loading")} rows={4} />
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const report = query.data
  const rows = report.items.filter((item) => item.parent === code)
  const current = code ? report.items.find((item) => item.code === code) : undefined
  if (report.items.length === 0) {
    return <EmptyState headingLevel={2} title={t("categories.empty")} />
  }
  const columns: DataColumn[] = [
    { key: "category", label: t("categories.columns.category") },
    { key: "offers", label: t("categories.columns.offers"), numeric: true },
    { key: "share", label: t("categories.columns.share"), numeric: true },
    { key: "companies", label: t("categories.columns.companies"), numeric: true },
    { key: "sellers", label: t("categories.columns.sellers"), numeric: true },
    { key: "fresh", label: t("categories.columns.fresh"), numeric: true },
    { key: "priced", label: t("categories.columns.priced"), numeric: true },
    { key: "searchable", label: t("categories.columns.searchable"), numeric: true },
  ]
  const search = writeFilters(scope.filters)
  const hrefOf = (item: Category) => {
    if (!item.code) return recordsHref(scope.filters, { problem: "no_category" })
    if (item.code.length <= 2) return analyticsCategoryPath(item.code, search)
    return recordsHref(scope.filters, { category: item.code })
  }
  const origins = ORIGINS.map((key) => ({
    key,
    label: t(`categories.origin.${key}`),
    value: report.origins.find((row) => row.key === key)?.count ?? 0,
  })).filter((bar) => bar.value > 0)
  return (
    <Reveal active>
      <Stack gap="wide">
        <SnapshotBar
          meta={report.meta}
          refreshing={query.isFetching}
          onRefresh={scope.refresh}
        />
        <nav className={styles.path} aria-label={t("categories.path")}>
          <Link to={`${ANALYTICS_CATEGORIES_PATH}${search}`}>{t("categories.all")}</Link>
          {current ? <span>{`${current.code} ${current.name}`.trim()}</span> : null}
          {current ? (
            <Link to={recordsHref(scope.filters, { category: current.code })}>
              {t("categories.showRecords")}
            </Link>
          ) : null}
        </nav>
        <DataTable
          label={
            current ? t("categories.children", { code: current.code }) : t("categories.title")
          }
          columns={columns}
        >
          {rows.map((item) => (
            <tr key={item.code || "none"}>
              <DataCell>
                <QuietLink to={hrefOf(item)}>
                  {item.code ? `${item.code} ${item.name}`.trim() : t("categories.noCategory")}
                </QuietLink>
              </DataCell>
              <DataCell numeric>{number(item.offers)}</DataCell>
              <DataCell numeric>
                <RatioCell ratio={item.share} />
              </DataCell>
              <DataCell numeric>{number(item.companies)}</DataCell>
              <DataCell numeric>
                <RatioCell ratio={item.verifiedSellers} />
              </DataCell>
              <DataCell numeric>
                <RatioCell ratio={item.fresh} />
              </DataCell>
              <DataCell numeric>
                <RatioCell ratio={item.priced} />
              </DataCell>
              <DataCell numeric>
                <RatioCell ratio={item.searchable} />
              </DataCell>
            </tr>
          ))}
        </DataTable>
        <p className={styles.note}>{t("categories.companiesNote")}</p>
        <PanelBlock framed title={t("categories.origins")}>
          <BarList bars={origins} total={report.offers} />
        </PanelBlock>
      </Stack>
    </Reveal>
  )
}
