import { useTranslation } from "react-i18next"
import {
  type AnalyticsFilters,
  SOURCE_TYPES,
  type SourceSummary,
} from "@/entities/analytics/model"
import { hasFilters } from "@/entities/analytics/scope"
import { useRegionGroups } from "@/features/search-box/region-preference/region-groups"
import { LOCALE_TAGS } from "@/shared/i18n/locale"
import { Combobox, type ComboboxGroup } from "@/shared/ui/combobox"
import { FilterNote } from "@/shared/ui/filter-note"
import styles from "./styles.module.css"

const ALL = ""

export type ScopeBarProps = {
  readonly filters: AnalyticsFilters
  readonly sources: readonly SourceSummary[]
  readonly onChange: (filters: AnalyticsFilters) => void
}

function allOption(label: string): ComboboxGroup {
  return { key: "all", options: [{ key: "all", value: ALL, label }] }
}

export function ScopeBar({ filters, sources, onChange }: ScopeBarProps) {
  const { t } = useTranslation("analytics")
  const { locale, groups: regionGroups } = useRegionGroups()
  const tag = LOCALE_TAGS[locale]
  const shared = {
    empty: t("scope.empty"),
    emptyHint: t("scope.emptyHint"),
    close: t("scope.close"),
  }
  const sourceName = sources.find((source) => source.sourceId === filters.sourceId)?.name
  const typeName = filters.sourceType ? t(`sourceType.${filters.sourceType}`) : undefined
  const regionName = filters.region
    ? (regionGroups
        .flatMap((group) => group.options)
        .find((option) => option.value === filters.region)?.label ?? filters.region)
    : undefined
  const pill = (label: string, value: string | undefined, fallback: string) =>
    t("scope.pill", { name: label, value: value ?? fallback })
  const sourceLabel = pill(t("scope.source"), sourceName, t("scope.allSources"))
  const typeLabel = pill(t("scope.sourceType"), typeName, t("scope.allTypes"))
  const regionLabel = pill(t("scope.region"), regionName, t("scope.allRegions"))
  return (
    <section className={styles.bar} aria-label={t("scope.legend")}>
      <div className={styles.fields}>
        <Combobox
          icon="database"
          value={filters.sourceId ?? ALL}
          valueLabel={sourceLabel}
          locale={tag}
          groups={[
            allOption(t("scope.allSources")),
            {
              key: "sources",
              label: t("scope.sources"),
              options: sources.map((source) => ({
                key: source.sourceId,
                value: source.sourceId,
                label: source.name,
              })),
            },
          ]}
          text={{
            ...shared,
            label: t("scope.source"),
            trigger: sourceLabel,
            search: t("scope.searchSource"),
          }}
          onChange={(value) => onChange({ ...filters, sourceId: value || undefined })}
        />
        <Combobox
          icon="filter"
          value={filters.sourceType ?? ALL}
          valueLabel={typeLabel}
          locale={tag}
          groups={[
            allOption(t("scope.allTypes")),
            {
              key: "types",
              label: t("scope.types"),
              options: SOURCE_TYPES.map((type) => ({
                key: type,
                value: type,
                label: t(`sourceType.${type}`),
              })),
            },
          ]}
          text={{
            ...shared,
            label: t("scope.sourceType"),
            trigger: typeLabel,
            search: t("scope.searchType"),
          }}
          onChange={(value) =>
            onChange({ ...filters, sourceType: SOURCE_TYPES.find((type) => type === value) })
          }
        />
        <Combobox
          icon="pin"
          value={filters.region ?? ALL}
          valueLabel={regionLabel}
          locale={tag}
          groups={[
            allOption(t("scope.allRegions")),
            ...regionGroups.filter((group) => group.key !== "none"),
          ]}
          text={{
            ...shared,
            label: t("scope.region"),
            trigger: regionLabel,
            search: t("scope.searchRegion"),
            hint: t("scope.regionNote"),
          }}
          onChange={(value) => onChange({ ...filters, region: value || undefined })}
        />
      </div>
      {hasFilters(filters) ? (
        <FilterNote
          text={t("scope.applied")}
          resetLabel={t("scope.reset")}
          onReset={() => onChange({})}
        />
      ) : null}
    </section>
  )
}
