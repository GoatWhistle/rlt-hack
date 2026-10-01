import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { PAGE_SIZE } from "@/entities/upload/list-query"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type PaginationProps = {
  readonly page: number
  readonly pages: number
  readonly total: number
  readonly hrefFor: (page: number) => string
}

const FULL_WINDOW = 7

export function pageItems(page: number, pages: number): readonly number[] {
  if (pages <= FULL_WINDOW) return Array.from({ length: pages }, (_, index) => index + 1)
  const around = [page - 1, page, page + 1].filter((item) => item > 1 && item < pages)
  const items = [1, ...around, pages]
  return items.flatMap((item, index) => {
    const previous = items[index - 1]
    return previous !== undefined && item - previous > 1 ? [-item, item] : [item]
  })
}

type StepProps = {
  readonly target: number
  readonly enabled: boolean
  readonly icon: IconName
  readonly label: string
  readonly hrefFor: (page: number) => string
}

function Step({ target, enabled, icon, label, hrefFor }: StepProps) {
  if (!enabled) {
    return (
      <span className={styles.step} data-disabled="true" aria-hidden="true">
        <Icon name={icon} size="sm" />
      </span>
    )
  }
  return (
    <Link to={hrefFor(target)} className={styles.step} aria-label={label}>
      <Icon name={icon} size="sm" />
    </Link>
  )
}

export function Pagination({ page, pages, total, hrefFor }: PaginationProps) {
  const { t } = useTranslation("lots")
  const { number } = useFormatters()
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const to = Math.min(total, page * PAGE_SIZE)
  return (
    <nav className={styles.pagination} aria-label={t("pages.label")}>
      <span className={styles.range}>{t("pages.range", { from, to, total })}</span>
      {pages > 1 ? (
        <ul className={styles.list}>
          <li>
            <Step
              target={page - 1}
              enabled={page > 1}
              icon="arrowLeft"
              label={t("pages.prev")}
              hrefFor={hrefFor}
            />
          </li>
          {pageItems(page, pages).map((item) =>
            item < 0 ? (
              <li key={item} className={styles.gap} aria-hidden="true">
                {t("pages.gap")}
              </li>
            ) : (
              <li key={item}>
                <Link
                  to={hrefFor(item)}
                  className={styles.number}
                  aria-label={t("pages.page", { page: item })}
                  aria-current={item === page ? "page" : undefined}
                >
                  {number(item)}
                </Link>
              </li>
            ),
          )}
          <li>
            <Step
              target={page + 1}
              enabled={page < pages}
              icon="arrowRight"
              label={t("pages.next")}
              hrefFor={hrefFor}
            />
          </li>
        </ul>
      ) : null}
    </nav>
  )
}
