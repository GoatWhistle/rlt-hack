import { useTranslation } from "react-i18next"
import { Link, Navigate } from "react-router"
import { useUploads } from "@/entities/upload/queries"
import { StatusStrip } from "@/entities/upload/status-strip"
import { UPLOADS_PATH, uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { ButtonLink } from "@/shared/ui/button"
import { ErrorState } from "@/shared/ui/error-state"
import { FactRow } from "@/shared/ui/fact-row"
import { FileName } from "@/shared/ui/file-name"
import { PageTitle } from "@/shared/ui/page-title"
import { RowChevron } from "@/shared/ui/row-chevron"
import { PageSkeleton } from "@/shared/ui/skeleton"
import styles from "./styles.module.css"

export const RECENT_UPLOADS = 5

export function LotsEntryPage() {
  const { t } = useTranslation("lots")
  const { dateTime } = useFormatters()
  const { t: common } = useTranslation()
  const uploads = useUploads()
  useDocumentTitle(common("title.lots"))

  if (uploads.isPending) return <PageSkeleton label={t("loading")} rows={3} />
  if (uploads.isError) {
    return (
      <ErrorState error={uploads.error} headingLevel={1} onRetry={() => uploads.refetch()} />
    )
  }
  const [only, ...others] = uploads.data
  if (!only) return <Navigate to={UPLOADS_PATH} replace />
  if (others.length === 0) return <Navigate to={uploadPath(only.id)} replace />

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <PageTitle>{t("entry.title")}</PageTitle>
        <p className={styles.lead}>{t("entry.text")}</p>
      </header>
      <ul className={styles.list} aria-label={t("entry.recent")}>
        {uploads.data.slice(0, RECENT_UPLOADS).map((upload) => (
          <li key={upload.id}>
            <Link to={uploadPath(upload.id)} className={styles.row}>
              <span className={styles.file}>
                <FileName name={upload.fileName} />
                <span className={styles.meta}>
                  <FactRow>
                    <span>{dateTime(upload.createdAt)}</span>
                    <span>{t("notices", { count: upload.total })}</span>
                  </FactRow>
                </span>
              </span>
              <span className={styles.strip}>
                <StatusStrip counts={upload.counts} total={upload.total} revealId={upload.id} />
              </span>
              <RowChevron className={styles.chevron} />
            </Link>
          </li>
        ))}
      </ul>
      {uploads.data.length > RECENT_UPLOADS ? (
        <ButtonLink to={UPLOADS_PATH} variant="secondary" className={styles.all}>
          {t("entry.all")}
        </ButtonLink>
      ) : null}
    </div>
  )
}
