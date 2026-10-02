import { useTranslation } from "react-i18next"
import type { FetchStatus, Run } from "@/entities/analytics/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { DataCell, type DataColumn, DataTable } from "@/shared/ui/data-table"
import type { IconName } from "@/shared/ui/icon"
import { MetaChip } from "@/shared/ui/meta-chip"
import styles from "./styles.module.css"

const STATUS_ICONS: Record<FetchStatus, IconName> = {
  success: "checkCircle",
  partial: "warning",
  failed: "warning",
}

export type RunsTableProps = { readonly runs: readonly Run[] }

export function RunsTable({ runs }: RunsTableProps) {
  const { t } = useTranslation("analytics")
  const { dateTime } = useFormatters()
  const columns: DataColumn[] = [
    { key: "source", label: t("sources.columns.source") },
    { key: "status", label: t("sources.columns.status") },
    { key: "started", label: t("sources.columns.started") },
    { key: "duration", label: t("sources.columns.duration"), numeric: true },
    { key: "extracted", label: t("sources.columns.extracted") },
  ]
  return (
    <DataTable label={t("sources.runsTitle")} columns={columns}>
      {runs.map((run) => (
        <tr key={run.runId}>
          <DataCell>
            <span>{run.sourceName}</span>
            {run.errorMessage ? <span className={styles.error}>{run.errorMessage}</span> : null}
          </DataCell>
          <DataCell>
            <MetaChip
              icon={STATUS_ICONS[run.status]}
              tone={run.status === "success" ? "accent" : "neutral"}
            >
              {t(`sources.status.${run.status}`)}
            </MetaChip>
          </DataCell>
          <DataCell>{dateTime(run.startedAt)}</DataCell>
          <DataCell numeric>{t("sources.duration", { seconds: run.durationSeconds })}</DataCell>
          <DataCell>
            {t("sources.extracted", {
              suppliers: run.suppliersExtracted,
              offers: run.offersExtracted,
            })}
          </DataCell>
        </tr>
      ))}
    </DataTable>
  )
}
