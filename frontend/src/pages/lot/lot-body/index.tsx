import { useTranslation } from "react-i18next"
import type { LotDetail } from "@/entities/upload/model"
import { EmptyState } from "@/shared/ui/empty-state"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import { Workspace } from "../workspace"
import styles from "./styles.module.css"

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

export type LotBodyProps = {
  readonly uploadId: string
  readonly detail: LotDetail
  readonly switching: boolean
}

export function LotBody({ uploadId, detail, switching }: LotBodyProps) {
  const { t } = useTranslation("lot")
  const { lot, recommendation } = detail
  return (
    <div className={styles.body} aria-busy={switching} inert={switching}>
      {switching ? (
        <span role="status">
          <VisuallyHidden>{t("loading")}</VisuallyHidden>
        </span>
      ) : null}
      {recommendation ? (
        <Workspace
          key={lot.id}
          uploadId={uploadId}
          lotId={lot.id}
          recommendation={recommendation}
        />
      ) : (
        <PendingState failed={lot.status === "failed"} />
      )}
    </div>
  )
}
