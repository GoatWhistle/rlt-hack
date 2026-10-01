import { useTranslation } from "react-i18next"
import { IssueList } from "@/entities/notice/issue-list"
import { isProcessing, type UploadDetail } from "@/entities/upload/model"
import { Caption } from "@/shared/ui/caption"
import { DoneNote } from "@/shared/ui/done-note"
import { Icon } from "@/shared/ui/icon"
import { ProgressBar } from "@/shared/ui/progress-bar"
import styles from "./styles.module.css"

export function ProcessingLine({ upload }: { readonly upload: UploadDetail }) {
  const { t } = useTranslation("lots")
  const running = isProcessing(upload)
  return (
    <div className={styles.line}>
      <div className={styles.progress}>
        {running ? (
          <span className={styles.bar}>
            <ProgressBar
              label={t("processing.label")}
              value={upload.processed}
              max={upload.total}
            />
          </span>
        ) : null}
        <p role="status" className={styles.status}>
          {running ? (
            <span className={styles.text}>
              {t("processing.running", { processed: upload.processed, total: upload.total })}
            </span>
          ) : (
            <DoneNote>{t("processing.done", { count: upload.total })}</DoneNote>
          )}
        </p>
      </div>
      {running ? <Caption>{t("processing.hint")}</Caption> : null}
      {upload.issues.length > 0 ? (
        <details className={styles.issues}>
          <summary className={styles.summary}>
            <Icon name="warning" size="sm" tone="warning" />
            {t("rejected", { count: upload.rejected })}
            <Icon name="chevron" size="sm" />
          </summary>
          <div className={styles.issueBody}>
            <Caption>{t("rejectedNote")}</Caption>
            <IssueList issues={upload.issues} />
          </div>
        </details>
      ) : null}
    </div>
  )
}
