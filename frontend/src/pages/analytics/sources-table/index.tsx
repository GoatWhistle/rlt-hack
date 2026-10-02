import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { AnalyticsFilters, SourceState, SourceSummary } from "@/entities/analytics/model"
import { recordsHref } from "@/entities/analytics/scope"
import { useFormatters } from "@/shared/i18n/formatters"
import { DataCell, type DataColumn, DataTable } from "@/shared/ui/data-table"
import type { IconName } from "@/shared/ui/icon"
import { MetaChip, type MetaChipTone } from "@/shared/ui/meta-chip"
import { RatioCell } from "../ratio-figure"
import styles from "./styles.module.css"

const STATE_FACES: Record<SourceState, { icon: IconName; tone: MetaChipTone }> = {
  ok: { icon: "checkCircle", tone: "accent" },
  partial: { icon: "warning", tone: "neutral" },
  failed: { icon: "warning", tone: "neutral" },
  never_run: { icon: "clock", tone: "muted" },
}

export type SourcesTableProps = {
  readonly sources: readonly SourceSummary[]
  readonly filters: AnalyticsFilters
  readonly compact?: boolean
}

export function SourcesTable({ sources, filters, compact = false }: SourcesTableProps) {
  const { t } = useTranslation("analytics")
  const { number, dateTime } = useFormatters()
  const columns: DataColumn[] = [
    { key: "source", label: t("sources.columns.source") },
    { key: "state", label: t("sources.columns.state") },
    { key: "offers", label: t("sources.columns.offers"), numeric: true },
    { key: "fresh", label: t("sources.columns.fresh"), numeric: true },
    { key: "success", label: t("sources.columns.lastSuccess") },
    ...(compact
      ? []
      : [
          { key: "type", label: t("sources.columns.type") },
          { key: "companies", label: t("sources.columns.companies"), numeric: true },
          { key: "attempt", label: t("sources.columns.lastAttempt") },
          { key: "failed", label: t("sources.columns.failed"), numeric: true },
        ]),
  ]
  const when = (value?: string) => (value ? dateTime(value) : t("sources.never"))
  return (
    <DataTable label={t("sources.title")} columns={columns}>
      {sources.map((source) => (
        <tr key={source.sourceId}>
          <DataCell>
            <Link
              to={recordsHref({ ...filters, sourceId: source.sourceId })}
              className={styles.link}
            >
              {source.name}
            </Link>
          </DataCell>
          <DataCell>
            <MetaChip
              icon={STATE_FACES[source.state].icon}
              tone={STATE_FACES[source.state].tone}
            >
              {t(`sources.state.${source.state}`)}
            </MetaChip>
          </DataCell>
          <DataCell numeric>{number(source.offers)}</DataCell>
          <DataCell numeric>
            <RatioCell ratio={source.fresh} />
          </DataCell>
          <DataCell>{when(source.lastSuccessAt)}</DataCell>
          {compact ? null : (
            <>
              <DataCell>{t(`sourceType.${source.sourceType}`)}</DataCell>
              <DataCell numeric>{number(source.companies)}</DataCell>
              <DataCell>{when(source.lastAttemptAt)}</DataCell>
              <DataCell numeric>{number(source.failedRuns)}</DataCell>
            </>
          )}
        </tr>
      ))}
    </DataTable>
  )
}
