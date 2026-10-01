import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { UploadSummary } from "@/entities/upload/model"
import { UPLOADS_PATH } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type LotsHeaderProps = {
  readonly upload: UploadSummary
  readonly onExport: () => void
  readonly status: ReactNode
}

export function LotsHeader({ upload, onExport, status }: LotsHeaderProps) {
  const { t } = useTranslation("lots")
  const { dateTime } = useFormatters()
  return (
    <header className={styles.header}>
      <BackLink to={UPLOADS_PATH}>{t("back")}</BackLink>
      <div className={styles.top}>
        <div className={styles.titles}>
          <h1 className={styles.title}>{upload.fileName}</h1>
          <p className={styles.meta}>
            {t("uploaded", { date: dateTime(upload.createdAt) })}
            {" · "}
            {t("notices", { count: upload.total })}
          </p>
          {status}
        </div>
        <Button variant="secondary" onClick={onExport} className={styles.action}>
          <Icon name="download" />
          {t("download")}
        </Button>
      </div>
    </header>
  )
}
