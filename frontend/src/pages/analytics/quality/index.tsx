import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { Problem, RecordProblem } from "@/entities/analytics/model"
import { useQuality } from "@/entities/analytics/queries"
import { recordsHref } from "@/entities/analytics/scope"
import { useFormatters } from "@/shared/i18n/formatters"
import { DataCell, type DataColumn, DataTable } from "@/shared/ui/data-table"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Reveal } from "@/shared/ui/reveal"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { BarList } from "../bar-list"
import { MetricCard } from "../metric-card"
import { useRatioText } from "../ratio-figure"
import { SnapshotBar } from "../snapshot-bar"
import { useScope } from "../use-scope"
import styles from "./styles.module.css"

const AGE_KEYS = ["d1", "d7", "d30", "older", "unknown"] as const
const AVAILABILITY_KEYS = ["available", "on_order", "unavailable", "unknown"] as const

const MATRIX: readonly { key: keyof Problem; label: string; problem: RecordProblem }[] = [
  { key: "noSupplier", label: "noSupplier", problem: "no_supplier" },
  { key: "unverifiedSeller", label: "unverifiedSeller", problem: "unverified_seller" },
  { key: "noCategory", label: "noCategory", problem: "no_category" },
  { key: "noPrice", label: "noPrice", problem: "no_price" },
  { key: "noAttributes", label: "noAttributes", problem: "no_attributes" },
  { key: "stale", label: "stale", problem: "stale" },
  { key: "unknownAge", label: "unknownAge", problem: "unknown_age" },
]

export function QualityPage() {
  const { t } = useTranslation("analytics")
  const { number } = useFormatters()
  const scope = useScope()
  const query = useQuality(scope.filters)
  const priced = useRatioText(
    query.data?.priced ?? { numerator: 0, denominator: 0, unknown: 0, share: null },
  )
  if (query.isPending) {
    return <PageSkeleton label={t("state.loading")} rows={4} />
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const report = query.data
  if (report.problems.length === 0) {
    return <EmptyState headingLevel={2} title={t("quality.empty")} />
  }
  const columns: DataColumn[] = [
    { key: "source", label: t("quality.columns.source") },
    { key: "offers", label: t("quality.columns.offers"), numeric: true },
    ...MATRIX.map((cell) => ({
      key: cell.key,
      label: t(`quality.columns.${cell.label as "noSupplier"}`),
      numeric: true,
    })),
  ]
  const bars = (
    keys: readonly string[],
    rows: typeof report.age,
    label: (key: string) => string,
  ) =>
    keys.map((key) => ({
      key,
      label: label(key),
      value: rows.find((row) => row.key === key)?.count ?? 0,
    }))
  return (
    <Reveal active>
      <div className={styles.page}>
        <SnapshotBar
          meta={report.meta}
          refreshing={query.isFetching}
          onRefresh={scope.refresh}
        />
        <MetricCard
          label={t("quality.priced")}
          value={priced.value}
          basis={priced.empty ? undefined : priced.basis}
          empty={priced.empty}
          hint={t("hints.priced")}
        />
        <div className={styles.pair}>
          <PanelBlock title={t("quality.ageTitle")}>
            <BarList
              total={report.offers}
              bars={bars(AGE_KEYS, report.age, (key) => t(`quality.age.${key as "d1"}`))}
            />
            <p className={styles.note}>{t("quality.ageNote")}</p>
          </PanelBlock>
          <PanelBlock title={t("quality.availabilityTitle")}>
            <BarList
              total={report.offers}
              bars={bars(AVAILABILITY_KEYS, report.availability, (key) =>
                t(`quality.availability.${key as "unknown"}`),
              )}
            />
          </PanelBlock>
        </div>
        <PanelBlock title={t("quality.matrixTitle")}>
          <DataTable label={t("quality.matrixTitle")} columns={columns}>
            {report.problems.map((row) => (
              <tr key={row.sourceId}>
                <DataCell>{row.name}</DataCell>
                <DataCell numeric>{number(row.offers)}</DataCell>
                {MATRIX.map((cell) => (
                  <DataCell key={cell.key} numeric>
                    <Link
                      to={recordsHref(
                        { ...scope.filters, sourceId: row.sourceId },
                        { problem: cell.problem },
                      )}
                      className={styles.link}
                    >
                      {number(row[cell.key] as number)}
                    </Link>
                  </DataCell>
                ))}
              </tr>
            ))}
          </DataTable>
          <p className={styles.note}>{t("quality.matrixNote")}</p>
        </PanelBlock>
      </div>
    </Reveal>
  )
}
