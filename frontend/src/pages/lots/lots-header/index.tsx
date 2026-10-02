import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { UploadSummary } from "@/entities/upload/model"
import { historyPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button } from "@/shared/ui/button"
import { FactRow } from "@/shared/ui/fact-row"
import { Icon } from "@/shared/ui/icon"
import { PageTitle } from "@/shared/ui/page-title"
import styles from "./styles.module.css"

export type LotsHeaderProps = {
  readonly upload: UploadSummary
  readonly onExport: () => void
  readonly status: ReactNode
}

export function LotsHeader({ upload, onExport, status }: LotsHeaderProps) {
  const { t } = useTranslation("lots")
  const { date, dateTime } = useFormatters()
  return (
    <header className={styles.header}>
      <BackLink to={historyPath("files")}>{t("back")}</BackLink>
      <div className={styles.top}>
        <div className={styles.titles}>
          <PageTitle size="record" mono>
            {upload.fileName}
          </PageTitle>
          <p className={styles.meta}>
            <FactRow>
              <span className={styles.full}>
                {t("uploaded", { date: dateTime(upload.createdAt) })}
              </span>
              <span className={styles.short}>{date(upload.createdAt)}</span>
              <span>{t("notices", { count: upload.total })}</span>
            </FactRow>
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={onExport}
          className={styles.action}
          aria-label={t("download")}
        >
          <Icon name="download" />
          <span className={styles.label}>{t("download")}</span>
        </Button>
      </div>
      {status}
    </header>
  )
}
