import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { isTextQuery, TEXT_QUERY_LOT, type UploadSummary } from "@/entities/upload/model"
import { useUploads } from "@/entities/upload/queries"
import { historyPath, lotPath, uploadPath } from "@/shared/config/paths"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export const LATEST_COUNT = 3

export function latestOf(uploads: readonly UploadSummary[]): UploadSummary[] {
  return [...uploads]
    .sort((left, right) => Date.parse(right.createdAt) - Date.parse(left.createdAt))
    .slice(0, LATEST_COUNT)
}

function LatestLink({ upload }: { readonly upload: UploadSummary }) {
  const query = isTextQuery(upload)
  const label = query ? upload.title || upload.fileName : upload.fileName
  return (
    <Link
      to={query ? lotPath(upload.id, TEXT_QUERY_LOT) : uploadPath(upload.id)}
      className={styles.link}
      title={label}
    >
      <Icon name={query ? "search" : "file"} size="sm" />
      <span className={styles.label} data-file={query ? undefined : true}>
        {label}
      </span>
    </Link>
  )
}

export function LatestStrip() {
  const { t } = useTranslation("search")
  const uploads = useUploads()
  const latest = latestOf(uploads.data ?? [])
  if (latest.length === 0) return null
  return (
    <nav className={styles.strip} aria-label={t("latest.label")}>
      <span className={styles.title}>{t("latest.title")}</span>
      <ul className={styles.list}>
        {latest.map((upload) => (
          <li key={upload.id} className={styles.item}>
            <LatestLink upload={upload} />
          </li>
        ))}
      </ul>
      <Link to={historyPath()} className={styles.all}>
        {t("latest.all")}
        <Icon name="arrowRight" size="sm" />
      </Link>
    </nav>
  )
}
