import { useTranslation } from "react-i18next"
import { PAGE_SIZE } from "@/entities/upload/list-query"
import { IconLink } from "@/shared/ui/icon-link"
import styles from "./styles.module.css"

export type PaginationProps = {
  readonly page: number
  readonly pages: number
  readonly total: number
  readonly hrefFor: (page: number) => string
}

export function Pagination({ page, pages, total, hrefFor }: PaginationProps) {
  const { t } = useTranslation("lots")
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const to = Math.min(total, page * PAGE_SIZE)
  return (
    <nav className={styles.pagination} aria-label={t("pages.label")}>
      <span className={styles.range}>{t("pages.range", { from, to, total })}</span>
      {pages > 1 ? (
        <span className={styles.buttons}>
          {page > 1 ? (
            <IconLink to={hrefFor(page - 1)} icon="arrowLeft" label={t("pages.prev")} />
          ) : null}
          <span className={styles.current}>{t("pages.current", { page, pages })}</span>
          {page < pages ? (
            <IconLink to={hrefFor(page + 1)} icon="arrowRight" label={t("pages.next")} />
          ) : null}
        </span>
      ) : null}
    </nav>
  )
}
