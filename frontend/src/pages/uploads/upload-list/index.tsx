import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { isProcessing, type UploadSummary } from "@/entities/upload/model"
import { uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import { Caption } from "@/shared/ui/caption"
import { DoneNote } from "@/shared/ui/done-note"
import { Icon } from "@/shared/ui/icon"
import { ProgressBar } from "@/shared/ui/progress-bar"
import { SplitRow } from "@/shared/ui/split-row"
import { Tag } from "@/shared/ui/tag"
import styles from "./styles.module.css"

function UploadRow({ upload }: { readonly upload: UploadSummary }) {
  const { t } = useTranslation("uploads")
  const { date } = useFormatters()
  const running = isProcessing(upload)
  return (
    <li className={styles.item}>
      <Link to={uploadPath(upload.id)} className={styles.row}>
        <span className={styles.main}>
          <span className={styles.name}>{upload.fileName}</span>
          <span className={styles.meta}>
            {t("list.date", { date: date(upload.createdAt) })}
            {" · "}
            {t("list.notices", { count: upload.total })}
          </span>
        </span>
        <span className={styles.state}>
          {running ? (
            <>
              <span className={styles.progressText}>
                {t("list.processing", { processed: upload.processed, total: upload.total })}
              </span>
              <ProgressBar
                label={t("list.progress", { name: upload.fileName })}
                value={upload.processed}
                max={upload.total}
              />
            </>
          ) : (
            <DoneNote>{t("list.done")}</DoneNote>
          )}
          <span className={styles.counts}>
            <Tag tone="success">{t("list.ready", { count: upload.counts.ready })}</Tag>
            <Tag tone="warning">
              {t("list.needsCheck", { count: upload.counts.needsCheck })}
            </Tag>
            <Tag tone="tentative">
              {t("list.noCandidates", { count: upload.counts.noCandidates })}
            </Tag>
          </span>
          {upload.rejected > 0 ? (
            <span className={styles.rejected}>
              {t("list.rejected", { count: upload.rejected })}
            </span>
          ) : null}
          {upload.stored ? null : <Caption>{t("list.notStored")}</Caption>}
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
          <h1 className={styles.title}>{t("list.title")}</h1>
          <p className={styles.caption}>{t("list.caption")}</p>
        </div>
        <Button onClick={onUpload}>
          <Icon name="upload" />
          {t("list.upload")}
        </Button>
      </SplitRow>
      <ul className={styles.list}>
        {uploads.map((upload) => (
          <UploadRow key={upload.id} upload={upload} />
        ))}
      </ul>
    </div>
  )
}
