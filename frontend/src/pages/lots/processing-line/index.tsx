import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import { IssueList } from "@/entities/notice/issue-list"
import { isProcessing, type UploadDetail } from "@/entities/upload/model"
import { StatusStrip } from "@/entities/upload/status-strip"
import { Caption } from "@/shared/ui/caption"
import { DoneNote } from "@/shared/ui/done-note"
import { Icon } from "@/shared/ui/icon"
import { Transition } from "@/shared/ui/transition"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

function useFinished(running: boolean): boolean {
  const [state, setState] = useState({ running, finished: false })
  if (state.running !== running) {
    setState({ running, finished: state.running && !running })
  }
  return state.finished
}

function Lead({
  upload,
  finished,
}: {
  readonly upload: UploadDetail
  readonly finished: boolean
}) {
  const { t } = useTranslation("lots")
  if (isProcessing(upload)) {
    return (
      <span className={styles.lead} aria-hidden="true">
        <span key={upload.processed} className={styles.text}>
          {t("processing.running", { processed: upload.processed, total: upload.total })}
        </span>
        <span className={styles.hint}>{t("processing.hint")}</span>
      </span>
    )
  }
  return (
    <Transition show={finished} preset="slide" className={styles.lead}>
      <DoneNote pop>{t("processing.done", { count: upload.total })}</DoneNote>
    </Transition>
  )
}

export function ProcessingLine({ upload }: { readonly upload: UploadDetail }) {
  const { t } = useTranslation("lots")
  const [open, setOpen] = useState(false)
  const issuesId = useId()
  const running = isProcessing(upload)
  const finished = useFinished(running)
  const progress = t("processing.running", { processed: upload.processed, total: upload.total })
  return (
    <div className={styles.line}>
      <VisuallyHidden role="status">
        {running ? progress : t("processing.done", { count: upload.total })}
      </VisuallyHidden>
      <StatusStrip
        compact
        live={running}
        revealId={upload.id}
        counts={upload.counts}
        total={upload.total}
        lead={running || finished ? <Lead upload={upload} finished={finished} /> : undefined}
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
      {upload.issues.length > 0 ? (
        <div id={issuesId} className={styles.issues} hidden={!open}>
          <Caption>{t("rejectedNote")}</Caption>
          <IssueList issues={upload.issues} />
        </div>
      ) : null}
    </div>
  )
}
