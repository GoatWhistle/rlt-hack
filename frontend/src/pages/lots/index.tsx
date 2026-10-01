import { useEffect, useState } from "react"
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
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { LoadingState } from "@/shared/ui/loading-state"
import { TextButton } from "@/shared/ui/text-button"
import { LotsControls } from "./lots-controls"
import { LotsHeader } from "./lots-header"
import { LotsTable } from "./lots-table"
import { Pagination } from "./pagination"
import { ProcessingLine } from "./processing-line"
import { SelectionBar } from "./selection-bar"
import styles from "./styles.module.css"

type ExportState = { readonly open: boolean; readonly session: number }

export function LotsPage() {
  const { t } = useTranslation("lots")
  const { uploadId = "" } = useParams()
  const [params, setParams] = useSearchParams()
  const upload = useUpload(uploadId)
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set())
  const [exporting, setExporting] = useState<ExportState>({ open: false, session: 0 })
  const query = readQuery(params)

  useEffect(() => {
    if (upload.data) rememberUpload(upload.data.id)
  }, [upload.data])

  if (upload.isPending) return <LoadingState label={t("loading")} />
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
  const visible = filtered(data.lots, query)
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
      <LotsHeader upload={data} onExport={() => openExport()} />
      <ProcessingLine upload={data} />
      <LotsControls
        search={query.search}
        filter={query.filter}
        counts={filterCounts(searched(data.lots, query.search))}
        onSearch={(search) => update({ search })}
        onFilter={(filter: Filter) => update({ filter })}
      />
      {visible.length === 0 ? (
        <EmptyState
          headingLevel={2}
          title={t("empty.title")}
          description={t("empty.text")}
          actions={
            <TextButton onClick={() => update({ search: "", filter: "all" })}>
              {t("empty.reset")}
            </TextButton>
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
          />
          <Pagination
            page={page}
            pages={pages}
            total={visible.length}
            hrefFor={(target) => uploadPath(data.id, writeQuery({ ...query, page: target }))}
          />
        </>
      )}
      {selected.size > 0 ? (
        <SelectionBar
          count={selected.size}
          onExport={() => openExport()}
          onClear={() => setSelected(new Set())}
        />
      ) : null}
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
