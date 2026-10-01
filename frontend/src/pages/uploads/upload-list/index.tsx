import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { isProcessing, type UploadSummary } from "@/entities/upload/model"
import { StatusStrip } from "@/entities/upload/status-strip"
import { uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { DoneNote } from "@/shared/ui/done-note"
import { Icon } from "@/shared/ui/icon"
import { PageTitle } from "@/shared/ui/page-title"
import { SplitRow } from "@/shared/ui/split-row"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

function UploadState({ upload }: { readonly upload: UploadSummary }) {
  const { t } = useTranslation("uploads")
  if (!isProcessing(upload)) return <DoneNote>{t("list.done")}</DoneNote>
  return (
    <span className={styles.progressText}>
      {t("list.processing", { processed: upload.processed, total: upload.total })}
    </span>
  )
}

function UploadRow({ upload }: { readonly upload: UploadSummary }) {
  const { t } = useTranslation("uploads")
  const { dateTime, number } = useFormatters()
  const notices = t("list.notices", { count: upload.total })
  return (
    <li>
      <Link to={uploadPath(upload.id)} className={styles.row}>
        <span className={styles.file}>
          <span className={styles.name}>{upload.fileName}</span>
          {upload.rejected > 0 ? (
            <span className={styles.rejected}>
              {t("list.rejected", { count: upload.rejected })}
            </span>
          ) : null}
        </span>
        <span className={clsx(styles.meta, styles.compact)}>
          {t("list.date", { date: dateTime(upload.createdAt) })}
          {" · "}
          {notices}
        </span>
        <span className={clsx(styles.date, styles.wide)}>{dateTime(upload.createdAt)}</span>
        <span className={clsx(styles.count, styles.wide)}>
          <span aria-hidden="true">{number(upload.total)}</span>
          <VisuallyHidden>{notices}</VisuallyHidden>
        </span>
        <span className={styles.state}>
          <UploadState upload={upload} />
          {upload.stored ? null : <Caption>{t("list.notStored")}</Caption>}
        </span>
        <span className={styles.results}>
          <StatusStrip counts={upload.counts} total={upload.total} />
        </span>
        <span className={styles.chevron} aria-hidden="true">
          <Icon name="chevron" />
        </span>
      </Link>
    </li>
  )
}

export type UploadListProps = {
  readonly uploads: readonly UploadSummary[]
  readonly onUpload: () => void
}

export function UploadList({ uploads, onUpload }: UploadListProps) {
  const { t } = useTranslation("uploads")
  return (
    <div className={styles.page}>
      <SplitRow>
        <div className={styles.titles}>
          <PageTitle>{t("list.title")}</PageTitle>
          <p className={styles.caption}>{t("list.caption")}</p>
        </div>
        <Button onClick={onUpload}>
          <Icon name="upload" />
          {t("list.upload")}
        </Button>
      </SplitRow>
      <div className={styles.table}>
        <div className={clsx(styles.columns, styles.wide)} aria-hidden="true">
          <span>{t("list.columns.file")}</span>
          <span>{t("list.columns.uploaded")}</span>
          <span className={styles.end}>{t("list.columns.notices")}</span>
          <span>{t("list.columns.status")}</span>
          <span>{t("list.columns.results")}</span>
        </div>
        <ul className={styles.list} aria-label={t("list.title")}>
          {uploads.map((upload) => (
            <UploadRow key={upload.id} upload={upload} />
          ))}
        </ul>
      </div>
    </div>
  )
}
