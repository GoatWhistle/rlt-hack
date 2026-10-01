import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useParams } from "react-router"
import {
  filtered,
  type ListQuery,
  pageForIndex,
  readQuery,
  writeQuery,
} from "@/entities/upload/list-query"
import type { LotSummary } from "@/entities/upload/model"
import { useLot, useUpload } from "@/entities/upload/queries"
import { ExportDialog } from "@/features/export-results"
import { isApiError } from "@/shared/api/api-error"
import { lotPath, UPLOADS_PATH, uploadPath } from "@/shared/config/paths"
import { useLocale } from "@/shared/i18n/locale-provider"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { WorkspaceSkeleton } from "@/shared/ui/workspace-skeleton"
import { LotBody } from "./lot-body"
import { LotHeader, type Neighbours } from "./lot-header"
import styles from "./styles.module.css"

function LotMissing({ fileTo }: { readonly fileTo?: string }) {
  const { t } = useTranslation("lot")
  return (
    <EmptyState
      icon="search"
      title={t("missing.title")}
      description={t("missing.text")}
      actions={
        <>
          {fileTo ? <ButtonLink to={fileTo}>{t("missing.toFile")}</ButtonLink> : null}
          <ButtonLink to={UPLOADS_PATH} variant="secondary">
            {t("missing.toUploads")}
          </ButtonLink>
        </>
      }
    />
  )
}

export function neighboursOf(
  list: readonly LotSummary[],
  index: number,
  uploadId: string,
  query: ListQuery,
): Neighbours | undefined {
  if (index < 0) return undefined
  const link = (target: number) => {
    const item = list[target]
    return item
      ? lotPath(uploadId, item.id, writeQuery({ ...query, page: pageForIndex(target) }))
      : undefined
  }
  return { prev: link(index - 1), next: link(index + 1), index: index + 1, total: list.length }
}

function useLotSwitch(uploadId: string, lotId: string) {
  const lot = useLot(uploadId, lotId)
  const upload = useUpload(uploadId)
  const switching = lot.isPlaceholderData && lot.data?.lot.id !== lotId
  const incoming = switching ? upload.data?.lots.find((item) => item.id === lotId) : undefined
  return {
    lot,
    upload,
    switching,
    incoming,
    waiting: lot.isPending || (switching && !incoming),
  }
}

export function LotPage() {
  const { t } = useTranslation("lot")
  const { uploadId = "", lotId = "" } = useParams()
  const location = useLocation()
  const query = readQuery(new URLSearchParams(location.search))
  const { lot, upload, switching, incoming, waiting } = useLotSwitch(uploadId, lotId)
  const { locale } = useLocale()
  const [exporting, setExporting] = useState(false)

  if (waiting || lot.isPending) return <WorkspaceSkeleton label={t("loading")} />
  if (lot.isError) {
    if (isApiError(lot.error) && lot.error.status === 404) {
      return (
        <LotMissing
          fileTo={upload.isSuccess ? uploadPath(uploadId, writeQuery(query)) : undefined}
        />
      )
    }
    return <ErrorState error={lot.error} headingLevel={1} onRetry={() => lot.refetch()} />
  }

  const summary = lot.data.upload
  const current = incoming ?? lot.data.lot
  const list = upload.data ? filtered(upload.data.lots, query, locale) : []
  const index = list.findIndex((item) => item.id === current.id)
  const listSearch = writeQuery({ ...query, page: pageForIndex(index) })
  const neighbours = neighboursOf(list, index, uploadId, query)

  return (
    <div className={styles.page}>
      <LotHeader
        upload={summary}
        lot={current}
        backTo={uploadPath(uploadId, index < 0 ? writeQuery(query) : listSearch)}
        neighbours={neighbours}
        onExport={() => setExporting(true)}
      />
      <LotBody uploadId={uploadId} detail={lot.data} switching={switching} />
      <ExportDialog
        open={exporting}
        onClose={() => setExporting(false)}
        uploadId={uploadId}
        fileName={summary.fileName}
        lots={upload.data?.lots ?? [current]}
        currentLotId={current.id}
      />
    </div>
  )
}
