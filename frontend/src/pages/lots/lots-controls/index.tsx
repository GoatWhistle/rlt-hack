import { useId } from "react"
import { useTranslation } from "react-i18next"
import { FILTERS, type Filter } from "@/entities/upload/list-query"
import { Icon } from "@/shared/ui/icon"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import styles from "./styles.module.css"

export type LotsControlsProps = {
  readonly search: string
  readonly filter: Filter
  readonly counts: Readonly<Record<Filter, number>>
  readonly onSearch: (search: string) => void
  readonly onFilter: (filter: Filter) => void
}

export function LotsControls({
  search,
  filter,
  counts,
  onSearch,
  onFilter,
}: LotsControlsProps) {
  const { t } = useTranslation("lots")
  const searchId = useId()
  return (
    <div className={styles.controls}>
      <div className={styles.search}>
        <label htmlFor={searchId} className={styles.label}>
          {t("search.label")}
        </label>
        <span className={styles.field}>
          <Icon name="search" size="sm" />
          <input
            id={searchId}
            type="search"
            className={styles.input}
            value={search}
            placeholder={t("search.placeholder")}
            onChange={(event) => onSearch(event.target.value)}
          />
        </span>
      </div>
      <SegmentedControl
        legend={t("filter.legend")}
        value={filter}
        onChange={onFilter}
        options={FILTERS.map((value) => ({
          value,
          label: t(`filter.${value}`),
          count: counts[value],
        }))}
      />
    </div>
  )
}
