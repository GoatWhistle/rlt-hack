import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useLocation, useParams } from "react-router"
import type { Recommendation } from "@/entities/recommendation/model"
import { useShortlist } from "@/entities/shortlist/store"
import {
  filtered,
  type ListQuery,
  pageForIndex,
  readQuery,
  writeQuery,
} from "@/entities/upload/list-query"
import type { LotSummary } from "@/entities/upload/model"
import { useLot, useUpload } from "@/entities/upload/queries"
import { CompareButton } from "@/features/compare-candidates"
import { ExportDialog } from "@/features/export-results"
import { RecentPlaces } from "@/features/recent-places"
import { isApiError } from "@/shared/api/api-error"
import { historyPath, lotPath, uploadPath } from "@/shared/config/paths"
import { useLocale } from "@/shared/i18n/locale-provider"
import { useInView } from "@/shared/media/use-in-view"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { Reveal } from "@/shared/ui/reveal"
import { WorkspaceSkeleton } from "@/shared/ui/workspace-skeleton"
import { CompareDialog } from "./compare-dialog"
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
          <ButtonLink to={historyPath("files")} variant="secondary">
            {t("missing.toUploads")}
          </ButtonLink>
        </>
      }
    >
      <RecentPlaces />
    </EmptyState>
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

function useLotCompare(
  uploadId: string,
  lotId: string,
  recommendation: Recommendation | null | undefined,
  switching: boolean,
) {
  const shortlist = useShortlist(uploadId, lotId)
  const [open, setOpen] = useState(false)
  const shown = switching ? null : recommendation
  const chosen = (shown?.companies ?? []).filter((company) =>
    shortlist.ids.includes(company.id),
  )
  return { chosen, products: shown?.products ?? [], open, setOpen }
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
  const { t: common } = useTranslation()
  const { uploadId = "", lotId = "" } = useParams()
  const location = useLocation()
  const query = readQuery(new URLSearchParams(location.search))
  const { lot, upload, switching, incoming, waiting } = useLotSwitch(uploadId, lotId)
  const [late] = useState(lot.isPending)
  const { locale } = useLocale()
  const [exporting, setExporting] = useState({ open: false, session: 0 })
  const compare = useLotCompare(uploadId, lotId, lot.data?.recommendation, switching)
  const [actionsRef, actionsInView] = useInView<HTMLDivElement>()
  useDocumentTitle(common("title.lot", { id: lotId }))

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

  return (
    <Reveal active={late}>
      <div className={styles.page}>
        <LotHeader
          upload={summary}
          lot={current}
          backTo={uploadPath(uploadId, index < 0 ? writeQuery(query) : listSearch)}
          neighbours={neighboursOf(list, index, uploadId, query)}
          chosen={compare.chosen.length}
          actionsRef={actionsRef}
          onCompare={() => compare.setOpen(true)}
          onExport={() => setExporting((state) => ({ open: true, session: state.session + 1 }))}
        />
        <LotBody
          uploadId={uploadId}
          detail={lot.data}
          switching={switching}
          dockAction={
            actionsInView ? null : (
              <CompareButton
                compact
                count={compare.chosen.length}
                onCompare={() => compare.setOpen(true)}
              />
            )
          }
        />
        <ExportDialog
          key={exporting.session}
          open={exporting.open}
          onClose={() => setExporting((state) => ({ ...state, open: false }))}
          uploadId={uploadId}
          fileName={summary.fileName}
          lots={upload.data?.lots ?? [current]}
          currentLotId={current.id}
        />
        <CompareDialog
          open={compare.open && compare.chosen.length > 0}
          companies={compare.chosen}
          products={compare.products}
          onClose={() => compare.setOpen(false)}
        />
      </div>
    </Reveal>
  )
}
