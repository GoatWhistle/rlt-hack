import { useTranslation } from "react-i18next"
import { RESULT_STATUSES, type ResultStatus } from "@/entities/upload/model"
import { StatusStrip } from "@/entities/upload/status-strip"
import { useTimedStage } from "@/shared/motion/use-timed-stage"
import { Caption } from "@/shared/ui/caption"
import { FileName } from "@/shared/ui/file-name"
import styles from "./styles.module.css"

export const PROCESSING_STAGES = [
  { key: "send", at: 0 },
  { key: "match", at: 1500 },
  { key: "rank", at: 9000 },
  { key: "slow", at: 45000 },
] as const

const NOTHING_YET = Object.fromEntries(RESULT_STATUSES.map((status) => [status, 0])) as Record<
  ResultStatus,
  number
>

export type ProcessingViewProps = {
  readonly fileName: string
  readonly count: number
}

export function ProcessingView({ fileName, count }: ProcessingViewProps) {
  const { t } = useTranslation("uploads")
  const stage = useTimedStage(PROCESSING_STAGES, true)
  return (
    <div className={styles.view}>
      <p className={styles.file}>
        <FileName name={fileName} />
      </p>
      <p className={styles.title} role="status">
        {t("dialog.processing.title", { count })}
      </p>
      <StatusStrip counts={NOTHING_YET} total={count} live />
      {stage ? (
        <p key={stage} className={styles.stage} data-slow={stage === "slow" || undefined}>
          {t(`dialog.processing.stage.${stage}`)}
        </p>
      ) : null}
      <Caption>{t("dialog.processing.note")}</Caption>
    </div>
  )
}
