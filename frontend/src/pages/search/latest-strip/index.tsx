import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { isTextQuery, TEXT_QUERY_LOT, type UploadSummary } from "@/entities/upload/model"
import { useUploads } from "@/entities/upload/queries"
import { historyPath, lotPath, uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { ageOf } from "@/shared/time/age-groups"
import { Icon } from "@/shared/ui/icon"
import { Truncate } from "@/shared/ui/truncate"
import { SideTitle } from "../side-title"
import styles from "./styles.module.css"

export const LATEST_COUNT = 5

export function latestOf(uploads: readonly UploadSummary[]): UploadSummary[] {
  return [...uploads]
    .sort((left, right) => Date.parse(right.createdAt) - Date.parse(left.createdAt))
    .slice(0, LATEST_COUNT)
}

function LatestLink({ upload }: { readonly upload: UploadSummary }) {
  const { relative } = useFormatters()
  const query = isTextQuery(upload)
  const label = query ? upload.title || upload.fileName : upload.fileName
  const age = ageOf(upload.createdAt)
  return (
    <Link
      to={query ? lotPath(upload.id, TEXT_QUERY_LOT) : uploadPath(upload.id)}
      className={styles.link}
      title={label}
    >
      <span className={styles.kind} aria-hidden="true">
        <Icon name={query ? "search" : "file"} size="sm" />
      </span>
      <Truncate className={query ? undefined : styles.file}>{label}</Truncate>
      <span className={styles.age}>{relative(age.value, age.unit)}</span>
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
      <SideTitle>{t("latest.title")}</SideTitle>
      <ul className={styles.list}>
        {latest.map((upload) => (
          <li key={upload.id}>
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
