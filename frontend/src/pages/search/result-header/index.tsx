import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router"
import type { SearchResult } from "@/entities/search/model"
import { COMPARE_FROM, CompareButton } from "@/features/compare-candidates"
import { SearchBox, type SearchStage, StageLine } from "@/features/search-box"
import { lotPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { CountBadge } from "@/shared/ui/count-badge"
import { FactRow } from "@/shared/ui/fact-row"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type ResultHeaderProps = {
  readonly result: SearchResult
  readonly inputId: string
  readonly chosen: number
  readonly stage: SearchStage | null
  readonly actionsRef?: (node: HTMLDivElement | null) => void
  readonly onStage: (stage: SearchStage | null) => void
  readonly onExport: () => void
  readonly onCompare: () => void
  readonly onClear: () => void
}

export function ResultHeader(props: ResultHeaderProps) {
  const { result, inputId, chosen, stage, actionsRef, onStage, onExport, onCompare, onClear } =
    props
  const { t } = useTranslation("search")
  const { dateTime } = useFormatters()
  const navigate = useNavigate()
  return (
    <header className={styles.header}>
      <h1 className={styles.heading}>
        <VisuallyHidden>{t("header.title", { query: result.query.text })}</VisuallyHidden>
      </h1>
      <div className={styles.query}>
        <SearchBox
          key={result.searchId}
          compact
          shortcut
          inputId={inputId}
          initialText={result.query.text}
          initialRegion={result.query.preferredRegion}
          onStage={onStage}
          onFound={(next) => navigate(lotPath(next.id, "query"), { viewTransition: true })}
        />
      </div>
      {result.candidates.length > 0 ? (
        <div ref={actionsRef} className={styles.actions}>
          <CompareButton
            count={chosen}
            className={styles.action}
            labelClassName={styles.actionLabel}
            onCompare={onCompare}
          />
          <Button
            variant="secondary"
            className={styles.action}
            aria-label={t("header.export")}
            onClick={onExport}
          >
            <Icon name="download" />
            <span className={styles.actionLabel}>{t("header.export")}</span>
            {chosen > 0 ? <CountBadge value={chosen} corner /> : null}
          </Button>
        </div>
      ) : null}
      <p className={styles.meta}>
        <StageLine stage={stage} />
        {chosen > 0 ? <Selection chosen={chosen} onClear={onClear} /> : null}
        <time dateTime={result.createdAt}>{dateTime(result.createdAt)}</time>
      </p>
    </header>
  )
}

function Selection({
  chosen,
  onClear,
}: {
  readonly chosen: number
  readonly onClear: () => void
}) {
  const { t: candidate } = useTranslation("candidate")
  return (
    <span className={styles.selection}>
      <span aria-live="polite">
        <FactRow>
          <span>{candidate("selection.count", { count: chosen })}</span>
          {chosen < COMPARE_FROM ? (
            <span className={styles.more}>{candidate("selection.pickMore")}</span>
          ) : null}
        </FactRow>
      </span>
      <TextButton className={styles.clear} onClick={onClear}>
        {candidate("selection.clear")}
      </TextButton>
    </span>
  )
}
