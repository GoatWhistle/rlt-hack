import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { useRecentSearches } from "@/entities/search/queries"
import { useUploads } from "@/entities/upload/queries"
import { searchPath, uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { Stack } from "@/shared/ui/stack"
import { Truncate } from "@/shared/ui/truncate"
import styles from "./styles.module.css"

export const RECENT_FILES = 3

export function RecentPlaces() {
  const { t } = useTranslation()
  const { dateTime } = useFormatters()
  const titleId = useId()
  const uploads = useUploads()
  const searches = useRecentSearches(1)
  const files = uploads.data?.slice(0, RECENT_FILES) ?? []
  const search = searches.data?.[0]
  if (files.length === 0 && !search) return null
  return (
    <section className={styles.recent} aria-labelledby={titleId}>
      <h2 id={titleId} className={styles.title}>
        {t("recent.title")}
      </h2>
      <Stack as="ul" gap="tight">
        {files.map((upload) => (
          <li key={upload.id}>
            <Link to={uploadPath(upload.id)} className={styles.link}>
              <Icon name="fileCheck" size="sm" />
              <Truncate className={styles.file}>{upload.fileName}</Truncate>
              <span className={styles.meta}>{dateTime(upload.createdAt)}</span>
            </Link>
          </li>
        ))}
        {search ? (
          <li>
            <Link to={searchPath(search.searchId)} className={styles.link}>
              <Icon name="search" size="sm" />
              <Truncate>{search.text}</Truncate>
              <span className={styles.meta}>{t("recent.search")}</span>
            </Link>
          </li>
        ) : null}
      </Stack>
    </section>
  )
}
