import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useParams } from "react-router"
import { useUploadGateway } from "@/entities/upload/gateway-context"
import { filtered, pageForIndex, readQuery, writeQuery } from "@/entities/upload/list-query"
import { useLot, useUpload } from "@/entities/upload/queries"
import { ExportDialog } from "@/features/export-results"
import { isApiError } from "@/shared/api/api-error"
import { lotPath, UPLOADS_PATH, uploadPath } from "@/shared/config/paths"
import { useLocale } from "@/shared/i18n/locale-provider"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { WorkspaceSkeleton } from "@/shared/ui/workspace-skeleton"
import { LotHeader, type Neighbours } from "./lot-header"
import styles from "./styles.module.css"
import { Workspace } from "./workspace"

function PendingState({ failed }: { readonly failed: boolean }) {
  const { t } = useTranslation("lot")
  return failed ? (
    <EmptyState
      icon="warning"
      headingLevel={2}
      title={t("failed.title")}
      description={t("failed.text")}
    />
  ) : (
    <EmptyState
      icon="clock"
      headingLevel={2}
      title={t("queued.title")}
      description={t("queued.text")}
    />
  )
}

export function LotPage() {
  const { t } = useTranslation("lot")
  const { uploadId = "", lotId = "" } = useParams()
  const location = useLocation()
  const query = readQuery(new URLSearchParams(location.search))
  const lot = useLot(uploadId, lotId)
  const upload = useUpload(uploadId)
  const gateway = useUploadGateway()
  const { locale } = useLocale()
  const [exporting, setExporting] = useState({ open: false, session: 0 })

  if (lot.isPending) return <WorkspaceSkeleton label={t("loading")} />
  if (lot.isError) {
    if (isApiError(lot.error) && lot.error.status === 404) {
      return (
        <EmptyState
          icon="search"
          title={t("missing.title")}
          description={t("missing.text")}
          actions={
            <>
              {upload.isSuccess ? (
                <ButtonLink to={uploadPath(uploadId, writeQuery(query))}>
                  {t("missing.toFile")}
                </ButtonLink>
              ) : null}
              <ButtonLink to={UPLOADS_PATH} variant="secondary">
                {t("missing.toUploads")}
              </ButtonLink>
            </>
          }
        />
      )
    }
    return <ErrorState error={lot.error} headingLevel={1} onRetry={() => lot.refetch()} />
  }

  const { upload: summary, lot: current, recommendation } = lot.data
  const list = upload.data ? filtered(upload.data.lots, query, locale) : []
  const index = list.findIndex((item) => item.id === current.id)
  const listSearch = writeQuery({ ...query, page: pageForIndex(index) })
  const link = (target: number) => {
    const item = list[target]
    return item
      ? lotPath(uploadId, item.id, writeQuery({ ...query, page: pageForIndex(target) }))
      : undefined
  }
  const neighbours: Neighbours | undefined =
    index < 0
      ? undefined
      : { prev: link(index - 1), next: link(index + 1), index: index + 1, total: list.length }

  return (
    <div className={styles.page}>
      <LotHeader
        upload={summary}
        lot={current}
        backTo={uploadPath(uploadId, index < 0 ? writeQuery(query) : listSearch)}
        neighbours={neighbours}
        onExport={() => setExporting((state) => ({ open: true, session: state.session + 1 }))}
      />
      {recommendation ? (
        <Workspace
          key={current.id}
          uploadId={uploadId}
          lotId={current.id}
          recommendation={recommendation}
        />
      ) : (
        <PendingState failed={current.status === "failed"} />
      )}
      <ExportDialog
        key={exporting.session}
        open={exporting.open}
        onClose={() => setExporting((state) => ({ ...state, open: false }))}
        uploadId={uploadId}
        fileName={summary.fileName}
        lots={upload.data?.lots ?? [current]}
        currentLotId={current.id}
      />
    </div>
  )
}
