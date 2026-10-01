import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useParams, useSearchParams } from "react-router"
import { rememberUpload } from "@/entities/upload/last-upload"
import {
  type Filter,
  filterCounts,
  filtered,
  type ListQuery,
  pageCount,
  pageOf,
  readQuery,
  searched,
  writeQuery,
} from "@/entities/upload/list-query"
import { useUpload } from "@/entities/upload/queries"
import { ExportDialog } from "@/features/export-results"
import { isApiError } from "@/shared/api/api-error"
import { UPLOADS_PATH, uploadPath } from "@/shared/config/paths"
import { useLocale } from "@/shared/i18n/locale-provider"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { Button, ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { Icon } from "@/shared/ui/icon"
import { SelectionBar } from "@/shared/ui/selection-bar"
import { TextButton } from "@/shared/ui/text-button"
import { LotsControls } from "./lots-controls"
import { LotsHeader } from "./lots-header"
import { LotsSkeleton } from "./lots-skeleton"
import { LotsTable } from "./lots-table"
import { Pagination } from "./pagination"
import { ProcessingLine } from "./processing-line"
import styles from "./styles.module.css"

type ExportState = { readonly open: boolean; readonly session: number }
type Selection = { readonly uploadId: string; readonly ids: ReadonlySet<string> }

const NOTHING: ReadonlySet<string> = new Set()

export function LotsPage() {
  const { t } = useTranslation("lots")
  const { uploadId = "" } = useParams()
  const [params, setParams] = useSearchParams()
  const upload = useUpload(uploadId)
  const { locale } = useLocale()
  const pageToggle = useRef<HTMLInputElement>(null)
  const [selection, setSelection] = useState<Selection>({ uploadId, ids: NOTHING })
  const selected = selection.uploadId === uploadId ? selection.ids : NOTHING
  const setSelected = (change: (current: ReadonlySet<string>) => ReadonlySet<string>) =>
    setSelection((current) => ({
      uploadId,
      ids: change(current.uploadId === uploadId ? current.ids : NOTHING),
    }))
  const [exporting, setExporting] = useState<ExportState>({ open: false, session: 0 })
  const query = readQuery(params)
  const { t: common } = useTranslation()
  useDocumentTitle([upload.data?.fileName, common("title.lots")])

  useEffect(() => {
    if (upload.data) rememberUpload(upload.data.id)
  }, [upload.data])

  if (upload.isPending) return <LotsSkeleton />
  if (upload.isError) {
    if (isApiError(upload.error) && upload.error.status === 404) {
      return (
        <EmptyState
          title={t("missing.title")}
          description={t("missing.text")}
          actions={<ButtonLink to={UPLOADS_PATH}>{t("missing.action")}</ButtonLink>}
        />
      )
    }
    return <ErrorState error={upload.error} headingLevel={1} onRetry={() => upload.refetch()} />
  }

  const data = upload.data
  const visible = filtered(data.lots, query, locale)
  const pages = pageCount(visible.length)
  const page = Math.min(query.page, pages)
  const update = (next: Partial<ListQuery>) =>
    setParams(writeQuery({ ...query, page: 1, ...next }), { replace: true })
  const toggle = (lotId: string) =>
    setSelected((current) => {
      const next = new Set(current)
      if (!next.delete(lotId)) next.add(lotId)
      return next
    })
  const togglePage = (lotIds: readonly string[], checked: boolean) =>
    setSelected((current) => {
      const next = new Set(current)
      for (const id of lotIds) {
        if (checked) next.add(id)
        else next.delete(id)
      }
      return next
    })
  const openExport = () =>
    setExporting((current) => ({ open: true, session: current.session + 1 }))

  return (
    <div className={styles.page}>
      <LotsHeader
        upload={data}
        onExport={() => openExport()}
        status={<ProcessingLine upload={data} />}
      />
      <LotsControls
        search={query.search}
        filter={query.filter}
        counts={filterCounts(searched(data.lots, query.search, locale))}
        onSearch={(search) => update({ search })}
        onFilter={(filter: Filter) => update({ filter })}
      />
      {visible.length === 0 ? (
        <EmptyState
          headingLevel={2}
          title={
            query.search.trim()
              ? t("empty.query", { query: query.search.trim() })
              : t("empty.title")
          }
          description={
            query.filter === "all"
              ? t("empty.text")
              : t("empty.filtered", { filter: t(`filter.${query.filter}`) })
          }
          actions={
            <>
              <Button variant="secondary" onClick={() => update({ search: "", filter: "all" })}>
                {t("empty.reset")}
              </Button>
              {query.filter !== "all" && query.search.trim() ? (
                <TextButton onClick={() => update({ filter: "all" })}>
                  {t("empty.allStatuses")}
                </TextButton>
              ) : null}
            </>
          }
        />
      ) : (
        <>
          <LotsTable
            uploadId={data.id}
            fileName={data.fileName}
            lots={pageOf(visible, page)}
            linkSearch={writeQuery({ ...query, page })}
            selected={selected}
            onToggle={toggle}
            onTogglePage={togglePage}
            pageToggle={pageToggle}
          />
          <Pagination
            page={page}
            pages={pages}
            total={visible.length}
            hrefFor={(target) => uploadPath(data.id, writeQuery({ ...query, page: target }))}
          />
        </>
      )}
      <SelectionBar
        count={selected.size}
        label={t("selection.label")}
        countText={(count) => t("selection.count", { count })}
        clearLabel={t("selection.clear")}
        onClear={() => {
          setSelected(() => NOTHING)
          pageToggle.current?.focus()
        }}
      >
        <Button variant="strong" onClick={() => openExport()}>
          <Icon name="download" />
          {t("selection.export")}
        </Button>
      </SelectionBar>
      <ExportDialog
        key={exporting.session}
        open={exporting.open}
        onClose={() => setExporting((current) => ({ ...current, open: false }))}
        uploadId={data.id}
        fileName={data.fileName}
        lots={data.lots}
        selectedIds={[...selected]}
      />
    </div>
  )
}
