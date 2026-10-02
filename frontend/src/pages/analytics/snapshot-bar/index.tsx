import { useTranslation } from "react-i18next"
import type { SnapshotMeta } from "@/entities/analytics/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Button } from "@/shared/ui/button"
import styles from "./styles.module.css"

export type SnapshotBarProps = {
  readonly meta: SnapshotMeta
  readonly refreshing: boolean
  readonly onRefresh: () => void
}

export function SnapshotBar({ meta, refreshing, onRefresh }: SnapshotBarProps) {
  const { t } = useTranslation("analytics")
  const { dateTime } = useFormatters()
  const failed = meta.warnings.includes("refresh_failed")
  return (
    <div className={styles.bar}>
      <p className={styles.text}>
        <span>{t("snapshot.asOf", { time: dateTime(meta.asOf) })}</span>
        <span className={styles.muted}>
          {t("snapshot.delay", { time: dateTime(meta.computedAt) })}
        </span>
      </p>
      <Button variant="secondary" pending={refreshing} onClick={onRefresh}>
        {t("snapshot.refresh")}
      </Button>
      {failed ? (
        <p className={styles.warning} role="status">
          {t("snapshot.refreshFailed")}
        </p>
      ) : null}
    </div>
  )
}
