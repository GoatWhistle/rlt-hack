import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { type Overview, SOURCE_TYPES } from "@/entities/analytics/model"
import { useOverview } from "@/entities/analytics/queries"
import { hasFilters, recordsHref } from "@/entities/analytics/scope"
import { useFormatters } from "@/shared/i18n/formatters"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Reveal } from "@/shared/ui/reveal"
import { PageSkeleton } from "@/shared/ui/skeleton"
import { Stack } from "@/shared/ui/stack"
import { BarList } from "../bar-list"
import { MetricCard, MetricGroup } from "../metric-card"
import { useRatioText } from "../ratio-figure"
import { RunsTable } from "../runs-table"
import { SnapshotBar } from "../snapshot-bar"
import { SourcesTable } from "../sources-table"
import { useScope } from "../use-scope"
import { AttentionList } from "./attention"
import styles from "./styles.module.css"
import { TopCategories } from "./top-categories"

type RatioMetricProps = {
  readonly name: "fresh" | "searchable"
  readonly overview: Overview
  readonly href?: string
}

function RatioMetric({ name, overview, href }: RatioMetricProps) {
  const { t } = useTranslation("analytics")
  const ratio = useRatioText(overview[name])
  const { policy } = overview.meta
  return (
    <MetricCard
      label={t(`metrics.${name}`)}
      value={ratio.value}
      basis={ratio.empty ? undefined : ratio.basis}
      note={ratio.unknown}
      empty={ratio.empty}
      hint={t(`hints.${name}`, { offer: policy.offerDays, registry: policy.registryDays })}
      action={
        href ? (
          <Link to={href} className={styles.link}>
            {t("records.show")}
          </Link>
        ) : undefined
      }
    />
  )
}

export function OverviewPage() {
  const { t } = useTranslation("analytics")
  const { number } = useFormatters()
  const scope = useScope()
  const query = useOverview(scope.filters)
  if (query.isPending) return <PageSkeleton label={t("state.loading")} rows={3} />
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  }
  const overview = query.data
  if (overview.offers === 0) {
    const filtered = hasFilters(scope.filters)
    return (
      <EmptyState
        headingLevel={2}
        title={filtered ? t("state.emptyFilter") : t("state.empty")}
        description={filtered ? t("state.emptyFilterDescription") : t("state.emptyDescription")}
      />
    )
  }
  return (
    <Reveal active>
      <Stack gap="wide">
        <SnapshotBar
          meta={overview.meta}
          refreshing={query.isFetching}
          onRefresh={scope.refresh}
        />
        <MetricGroup>
          <MetricCard
            label={t("metrics.offers")}
            value={number(overview.offers)}
            hint={t("hints.offers")}
            action={
              <Link to={recordsHref(scope.filters)} className={styles.link}>
                {t("records.show")}
              </Link>
            }
          />
          <MetricCard
            label={t("metrics.companies")}
            value={number(overview.companies)}
            hint={t("hints.companies")}
          />
          <RatioMetric
            name="fresh"
            overview={overview}
            href={recordsHref(scope.filters, { problem: "stale" })}
          />
          <RatioMetric name="searchable" overview={overview} />
        </MetricGroup>
        <PanelBlock title={t("composition.title")}>
          <BarList
            total={overview.offers}
            bars={overview.composition.map((row) => {
              const type = SOURCE_TYPES.find((option) => option === row.key)
              return {
                key: row.key,
                label: type ? t(`sourceType.${type}`) : row.key,
                value: row.count,
              }
            })}
          />
        </PanelBlock>
        <AttentionList
          items={overview.attention}
          sources={overview.sources}
          filters={scope.filters}
        />
        <TopCategories
          categories={overview.categories}
          total={overview.offers}
          filters={scope.filters}
        />
        <PanelBlock title={t("sources.title")}>
          <SourcesTable sources={overview.sources} filters={scope.filters} compact />
        </PanelBlock>
        <PanelBlock title={t("sources.runsTitle")}>
          <RunsTable runs={overview.runs} />
        </PanelBlock>
      </Stack>
    </Reveal>
  )
}
