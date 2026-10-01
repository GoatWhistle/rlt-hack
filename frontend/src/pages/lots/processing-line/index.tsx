import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { IssueList } from "@/entities/notice/issue-list"
import { isProcessing, type UploadDetail } from "@/entities/upload/model"
import { StatusStrip } from "@/entities/upload/status-strip"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export function ProcessingLine({ upload }: { readonly upload: UploadDetail }) {
  const { t } = useTranslation("lots")
  const [open, setOpen] = useState(false)
  const issuesId = useId()
  const running = isProcessing(upload)
  const progress = t("processing.running", { processed: upload.processed, total: upload.total })
  return (
    <div className={styles.line}>
      <VisuallyHidden role="status">
        {running ? progress : t("processing.done", { count: upload.total })}
      </VisuallyHidden>
      <StatusStrip
        compact
        counts={upload.counts}
        total={upload.total}
        lead={
          running ? (
            <span className={styles.text} aria-hidden="true">
              {progress}
            </span>
          ) : undefined
        }
        trail={
          upload.issues.length > 0 ? (
            <button
              type="button"
              className={styles.toggle}
              aria-expanded={open}
              aria-controls={issuesId}
              onClick={() => setOpen((current) => !current)}
            >
              <Icon name="warning" size="sm" tone="warning" />
              {t("rejected", { count: upload.rejected })}
              <Icon name="chevron" size="sm" />
            </button>
          ) : undefined
        }
      />
      {running ? <Caption>{t("processing.hint")}</Caption> : null}
      {upload.issues.length > 0 ? (
        <div id={issuesId} className={styles.issues} hidden={!open}>
          <Caption>{t("rejectedNote")}</Caption>
          <IssueList issues={upload.issues} />
        </div>
      ) : null}
    </div>
  )
}
