import { useTranslation } from "react-i18next"
import {
  type AnalyticsFilters,
  SOURCE_TYPES,
  type SourceSummary,
  type SourceType,
} from "@/entities/analytics/model"
import { hasFilters } from "@/entities/analytics/scope"
import { SelectField, TextField } from "@/shared/ui/field"
import { FilterNote } from "@/shared/ui/filter-note"
import styles from "./styles.module.css"

const ALL = ""

export type ScopeBarProps = {
  readonly filters: AnalyticsFilters
  readonly sources: readonly SourceSummary[]
  readonly onChange: (filters: AnalyticsFilters) => void
}

export function ScopeBar({ filters, sources, onChange }: ScopeBarProps) {
  const { t } = useTranslation("analytics")
  const all = { value: ALL, label: t("scope.all") }
  const sourceOptions = [
    all,
    ...sources.map((source) => ({ value: source.sourceId, label: source.name })),
  ]
  const typeOptions = [
    all,
    ...SOURCE_TYPES.map((type) => ({ value: type, label: t(`sourceType.${type}`) })),
  ]
  return (
    <section className={styles.bar} aria-label={t("scope.legend")}>
      <div className={styles.fields}>
        <SelectField
          label={t("scope.source")}
          value={filters.sourceId ?? ALL}
          options={sourceOptions}
          onChange={(value) => onChange({ ...filters, sourceId: value || undefined })}
        />
        <SelectField
          label={t("scope.sourceType")}
          value={filters.sourceType ?? ALL}
          options={typeOptions}
          onChange={(value) =>
            onChange({
              ...filters,
              sourceType: SOURCE_TYPES.find((type): type is SourceType => type === value),
            })
          }
        />
        <TextField
          label={t("scope.region")}
          value={filters.region ?? ""}
          placeholder={t("scope.regionHint")}
          onCommit={(value) => onChange({ ...filters, region: value || undefined })}
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
