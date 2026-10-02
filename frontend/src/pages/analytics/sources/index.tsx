import { useTranslation } from "react-i18next"
import { useSources } from "@/entities/analytics/queries"
import { useFormatters } from "@/shared/i18n/formatters"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Reveal } from "@/shared/ui/reveal"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { useRatioText } from "../ratio-figure"
import { RunsTable } from "../runs-table"
import { SnapshotBar } from "../snapshot-bar"
import { SourcesTable } from "../sources-table"
import { useScope } from "../use-scope"
import styles from "./styles.module.css"

export function SourcesPage() {
  const { t } = useTranslation("analytics")
  const { number } = useFormatters()
  const scope = useScope()
  const query = useSources(scope.filters)
  const success = useRatioText(
    query.data?.success ?? { numerator: 0, denominator: 0, unknown: 0, share: null },
  )
  if (query.isPending) {
    return <PageSkeleton label={t("state.loading")} rows={4} />
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const report = query.data
  if (report.items.length === 0) {
    return <EmptyState headingLevel={2} title={t("sources.noSources")} />
  }
  return (
    <Reveal active>
      <div className={styles.page}>
        <SnapshotBar
          meta={report.meta}
          refreshing={query.isFetching}
          onRefresh={scope.refresh}
        />
        <PanelBlock
          title={t("sources.title")}
          aside={
            <span>
              {t("sources.runsSuccess", { days: report.meta.policy.periodDays })}:{" "}
              {success.value}
              {success.empty ? "" : ` (${success.basis})`}
              {report.partial > 0
                ? `, ${t("sources.runsPartial", { count: report.partial })}`
                : ""}
            </span>
          }
        >
          <SourcesTable sources={report.items} filters={scope.filters} />
          <p className={styles.note}>{t("sources.stateNote")}</p>
        </PanelBlock>
        <PanelBlock title={t("sources.runsTitle")} aside={number(report.runs.length)}>
          {report.runs.length === 0 ? (
            <p className={styles.note}>{t("sources.noRuns")}</p>
          ) : (
            <RunsTable runs={report.runs} />
          )}
          <p className={styles.note}>{t("sources.errorHidden")}</p>
        </PanelBlock>
      </div>
    </Reveal>
  )
}
