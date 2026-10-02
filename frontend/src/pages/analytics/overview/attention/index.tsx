import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { AnalyticsFilters, Attention, SourceSummary } from "@/entities/analytics/model"
import { recordsHref, writeFilters } from "@/entities/analytics/scope"
import { ANALYTICS_SOURCES_PATH } from "@/shared/config/paths"
import { PanelBlock } from "@/shared/ui/panel-block"
import styles from "./styles.module.css"

export type AttentionListProps = {
  readonly items: readonly Attention[]
  readonly sources: readonly SourceSummary[]
  readonly filters: AnalyticsFilters
}

export function attentionHref(item: Attention, filters: AnalyticsFilters): string {
  const scoped = item.sourceId ? { ...filters, sourceId: item.sourceId } : filters
  switch (item.code) {
    case "source_never_run":
    case "source_failed":
      return `${ANALYTICS_SOURCES_PATH}${writeFilters(scoped)}`
    case "source_stale":
      return recordsHref(scoped, { problem: "stale" })
    case "no_category":
      return recordsHref(scoped, { problem: "no_category" })
    case "no_verified_seller":
      return recordsHref(scoped, { problem: "unverified_seller" })
  }
}

export function AttentionList({ items, sources, filters }: AttentionListProps) {
  const { t } = useTranslation("analytics")
  const names = new Map(sources.map((source) => [source.sourceId, source.name]))
  return (
    <PanelBlock title={t("attention.title")}>
      {items.length === 0 ? (
        <p className={styles.none}>{t("attention.none")}</p>
      ) : (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={`${item.code}-${item.sourceId ?? "all"}`} className={styles.item}>
              <span>
                {t(`attention.${item.code}`, {
                  name: names.get(item.sourceId ?? "") ?? t("attention.unknownSource"),
                  count: item.count,
                  total: item.total,
                })}
              </span>
              <Link to={attentionHref(item, filters)} className={styles.link}>
                {t("attention.details")}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PanelBlock>
  )
}
