import { useTranslation } from "react-i18next"
import type { UploadSummary } from "@/entities/upload/model"
import { UPLOADS_PATH } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { SplitRow } from "@/shared/ui/split-row"
import styles from "./styles.module.css"

export type LotsHeaderProps = {
  readonly upload: UploadSummary
  readonly onExport: () => void
}

export function LotsHeader({ upload, onExport }: LotsHeaderProps) {
  const { t } = useTranslation("lots")
  const { date } = useFormatters()
  return (
    <header className={styles.header}>
      <BackLink to={UPLOADS_PATH}>{t("back")}</BackLink>
      <SplitRow>
        <div className={styles.titles}>
          <h1 className={styles.title}>{upload.fileName}</h1>
          <p className={styles.meta}>
            {t("uploaded", { date: date(upload.createdAt) })}
            {" · "}
            {t("notices", { count: upload.total })}
          </p>
        </div>
        <Button variant="secondary" onClick={onExport}>
          <Icon name="download" />
          {t("download")}
        </Button>
      </SplitRow>
    </header>
  )
}
