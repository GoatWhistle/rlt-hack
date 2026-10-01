import { useEffect, useId, useRef } from "react"
import { useTranslation } from "react-i18next"
import { FILTERS, type Filter } from "@/entities/upload/list-query"
import { useFormatters } from "@/shared/i18n/formatters"
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

const SHORTCUT = "/"

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
}

export function LotsControls({
  search,
  filter,
  counts,
  onSearch,
  onFilter,
}: LotsControlsProps) {
  const { t } = useTranslation("lots")
  const { number } = useFormatters()
  const searchId = useId()
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if (event.key !== SHORTCUT || event.ctrlKey || event.metaKey || event.altKey) return
      if (isTyping(event.target)) return
      event.preventDefault()
      input.current?.focus()
    }
    window.addEventListener("keydown", focusSearch)
    return () => window.removeEventListener("keydown", focusSearch)
  }, [])

  const clear = () => {
    onSearch("")
    input.current?.focus()
  }

  return (
    <div className={styles.controls}>
      <div className={styles.search}>
        <label htmlFor={searchId} className={styles.label}>
          {t("search.label")}
        </label>
        <span className={styles.field}>
          <Icon name="search" size="sm" />
          <input
            ref={input}
            id={searchId}
            type="search"
            className={styles.input}
            value={search}
            placeholder={t("search.placeholder")}
            aria-keyshortcuts={SHORTCUT}
            onChange={(event) => onSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape" && search) {
                event.preventDefault()
                onSearch("")
              }
            }}
          />
          {search ? (
            <button
              type="button"
              className={styles.clear}
              aria-label={t("search.clear")}
              onClick={clear}
            >
              <Icon name="close" size="sm" />
            </button>
          ) : (
            <span className={styles.key} aria-hidden="true">
              {t("search.shortcut")}
            </span>
          )}
        </span>
      </div>
      <div className={styles.filters}>
        <SegmentedControl
          scroll
          legend={t("filter.legend")}
          value={filter}
          onChange={onFilter}
          options={FILTERS.filter(
            (value) => value !== "failed" || counts.failed > 0 || filter === "failed",
          ).map((value) => ({
            value,
            label: t(`filter.${value}`),
            count: number(counts[value]),
          }))}
        />
      </div>
    </div>
  )
}
