import { useId } from "react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router"
import { isTextQuery, type UploadSummary } from "@/entities/upload/model"
import { useUploads } from "@/entities/upload/queries"
import {
  HISTORY_TAB_PARAM,
  HISTORY_TABS,
  type HistoryTab,
  SEARCH_PATH,
} from "@/shared/config/paths"
import { useMediaQuery } from "@/shared/media/use-media-query"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageTitle } from "@/shared/ui/page-title"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import { TextButton } from "@/shared/ui/text-button"
import { ColumnError, ColumnLoading } from "./column-state"
import { HistoryColumn } from "./history-column"
import { HistoryFilter } from "./history-filter"
import styles from "./styles.module.css"

export const HISTORY_FILTER_PARAM = "q"
export const WIDE_HISTORY = "(min-width: 64rem)"

function matches(upload: UploadSummary, filter: string): boolean {
  const needle = filter.trim().toLocaleLowerCase()
  if (!needle) return true
  return `${upload.title} ${upload.fileName}`.toLocaleLowerCase().includes(needle)
}

function tabOf(value: string | null): HistoryTab {
  return HISTORY_TABS.find((tab) => tab === value) ?? "queries"
}

export function HistoryPage() {
  const { t } = useTranslation("history")
  const { t: common } = useTranslation()
  useDocumentTitle(common("title.history"))
  const titleId = useId()
  const columnId = useId()
  const [params, setParams] = useSearchParams()
  const tab = tabOf(params.get(HISTORY_TAB_PARAM))
  const filter = params.get(HISTORY_FILTER_PARAM) ?? ""
  const wide = useMediaQuery(WIDE_HISTORY)
  const uploads = useUploads()

  const update = (key: string, value: string) =>
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (value) next.set(key, value)
        else next.delete(key)
        return next
      },
      { replace: true },
    )

  const all = uploads.data ?? []
  const shown = all.filter((upload) => matches(upload, filter))
  const queries = shown.filter(isTextQuery)
  const files = shown.filter((upload) => !isTextQuery(upload))
  const filtered = filter.trim() !== ""
  const state = uploads.isPending ? (
    <ColumnLoading />
  ) : uploads.isError && uploads.data === undefined ? (
    <ColumnError error={uploads.error} onRetry={() => uploads.refetch()} />
  ) : undefined
  const noMatch = (
    <EmptyState
      headingLevel={2}
      title={t("noMatch", { query: filter.trim() })}
      actions={
        <TextButton onClick={() => update(HISTORY_FILTER_PARAM, "")}>{t("reset")}</TextButton>
      }
    />
  )
  const start = (kind: "queries" | "files") => (
    <EmptyState
      headingLevel={2}
      icon={kind === "queries" ? "search" : "upload"}
      title={t(`${kind}.empty`)}
      description={t(`${kind}.emptyHint`)}
      actions={
        <ButtonLink variant="secondary" to={SEARCH_PATH}>
          {t(`${kind}.start`)}
        </ButtonLink>
      }
    />
  )

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div className={styles.intro}>
          <PageTitle id={titleId}>{t("title")}</PageTitle>
          <p className={styles.lead}>{t("lead")}</p>
        </div>
        <HistoryFilter
          value={filter}
          onChange={(value) => update(HISTORY_FILTER_PARAM, value)}
        />
      </header>
      {wide ? null : (
        <SegmentedControl
          block
          legend={t("tabs.legend")}
          value={tab}
          onChange={(next) => update(HISTORY_TAB_PARAM, next === "queries" ? "" : next)}
          options={HISTORY_TABS.map((value) => ({
            value,
            label: t(`${value}.title`),
            count: String(value === "queries" ? queries.length : files.length),
          }))}
        />
      )}
      <div className={styles.columns}>
        <HistoryColumn
          id={`${columnId}-queries`}
          title={t("queries.title")}
          uploads={queries}
          query
          hidden={!wide && tab !== "queries"}
          empty={filtered ? noMatch : start("queries")}
          state={state}
        />
        <HistoryColumn
          id={`${columnId}-files`}
          title={t("files.title")}
          uploads={files}
          query={false}
          hidden={!wide && tab !== "files"}
          empty={filtered ? noMatch : start("files")}
          state={state}
        />
      </div>
    </div>
  )
}
