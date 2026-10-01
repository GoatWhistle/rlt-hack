import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import type { SearchResult } from "@/entities/search/model"
import { SearchBox } from "@/features/search-box"
import { searchPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type ResultHeaderProps = {
  readonly result: SearchResult
  readonly inputId: string
  readonly chosen: number
  readonly onExport: () => void
}

export function ResultHeader({ result, inputId, chosen, onExport }: ResultHeaderProps) {
  const { t } = useTranslation("search")
  const { dateTime, number } = useFormatters()
  const navigate = useNavigate()
  const recommended = result.candidates.filter((item) => item.status === "recommended").length
  const facts = [
    t("items.count", { count: result.items.length }),
    t("recent.candidates", { count: result.candidates.length }),
    ...(recommended > 0 ? [t("recent.recommended", { count: recommended })] : []),
  ]
  return (
    <header className={styles.header}>
      <h1 className={styles.heading}>
        <VisuallyHidden>{t("header.title", { query: result.query.text })}</VisuallyHidden>
      </h1>
      <div className={styles.query}>
        <SearchBox
          key={result.searchId}
          compact
          inputId={inputId}
          showExamples={false}
          initialText={result.query.text}
          onFound={(next) => navigate(searchPath(next.searchId), { viewTransition: true })}
        />
      </div>
      {result.candidates.length > 0 ? (
        <Button
          variant="secondary"
          className={styles.export}
          aria-label={t("header.export")}
          onClick={onExport}
        >
          <Icon name="download" />
          <span className={styles.exportLabel}>{t("header.export")}</span>
          {chosen > 0 ? (
            <span key={chosen} className={styles.count}>
              {number(chosen)}
            </span>
          ) : null}
        </Button>
      ) : null}
      <p className={styles.meta}>
        <span>{facts.join(" · ")}</span>
        <time dateTime={result.createdAt}>{dateTime(result.createdAt)}</time>
      </p>
    </header>
  )
}
