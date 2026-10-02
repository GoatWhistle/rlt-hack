import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { SearchSummary } from "@/entities/search/model"
import { useRecentSearches } from "@/entities/search/queries"
import { searchPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { useFormatters } from "@/shared/i18n/formatters"
import { Dot } from "@/shared/ui/dot"
import { Icon } from "@/shared/ui/icon"
import { LoadingState } from "@/shared/ui/loading-state"
import { ResultSection } from "@/shared/ui/result-section"
import { TextButton } from "@/shared/ui/text-button"
import { RecentCollapse } from "../recent-toggle"
import styles from "./styles.module.css"

export function isToday(iso: string, now: Date = new Date()): boolean {
  const date = new Date(iso)
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  )
}

function Mix({ search }: { readonly search: SearchSummary }) {
  const check = Math.max(0, search.candidates - search.recommended)
  if (search.candidates === 0) return <Dot shape="dashed" tone="muted" />
  return (
    <span className={styles.mix} aria-hidden="true">
      {search.recommended > 0 ? (
        <span className={styles.recommended} style={{ flexGrow: search.recommended }} />
      ) : null}
      {check > 0 ? <span className={styles.check} style={{ flexGrow: check }} /> : null}
    </span>
  )
}

function RecentRow({ search }: { readonly search: SearchSummary }) {
  const { t } = useTranslation("search")
  const { dateTime } = useFormatters()
  const facts = [
    t("recent.items", { count: search.items }),
    search.candidates === 0
      ? t("recent.none")
      : t("recent.candidates", { count: search.candidates }),
    ...(search.recommended > 0 ? [t("recent.recommended", { count: search.recommended })] : []),
  ]
  return (
    <Link to={searchPath(search.searchId)} className={styles.row}>
      <span className={styles.text}>{search.text}</span>
      <span className={styles.meta}>
        <span className={styles.facts}>
          <Mix search={search} />
          {facts.join(" · ")}
        </span>
        <time dateTime={search.createdAt}>{dateTime(search.createdAt)}</time>
      </span>
      <span className={styles.chevron} aria-hidden="true">
        <Icon name="chevron" size="sm" />
      </span>
    </Link>
  )
}

function RecentGroup({
  title,
  searches,
}: {
  readonly title: string
  readonly searches: readonly SearchSummary[]
}) {
  if (searches.length === 0) return null
  return (
    <li className={styles.group}>
      <h3 className={styles.groupTitle}>{title}</h3>
      <ul className={styles.list}>
        {searches.map((search) => (
          <li key={search.searchId}>
            <RecentRow search={search} />
          </li>
        ))}
      </ul>
    </li>
  )
}

function RecentBody({ recent }: { readonly recent: ReturnType<typeof useRecentSearches> }) {
  const { t } = useTranslation("search")
  const errorMessage = useErrorMessage()
  if (recent.isPending) return <LoadingState label={t("loading")} />
  if (recent.isError) {
    return (
      <div className={styles.problem} role="alert">
        <span>{errorMessage(recent.error)}</span>
        <TextButton onClick={() => recent.refetch()}>{t("recent.retry")}</TextButton>
      </div>
    )
  }
  const today = recent.data.filter((search) => isToday(search.createdAt))
  const earlier = recent.data.filter((search) => !isToday(search.createdAt))
  return (
    <ul className={styles.groups}>
      <RecentGroup title={t("recent.today")} searches={today} />
      <RecentGroup title={t("recent.earlier")} searches={earlier} />
    </ul>
  )
}

export type RecentListProps = {
  readonly empty: ReactNode
  readonly controls?: string
  readonly onCollapse?: () => void
}

export function RecentList({ empty, controls, onCollapse }: RecentListProps) {
  const { t } = useTranslation("search")
  const recent = useRecentSearches()
  if (recent.isSuccess && recent.data.length === 0) return empty
  return (
    <ResultSection
      framed
      title={t("recent.title")}
      aside={
        controls && onCollapse ? (
          <RecentCollapse controls={controls} onCollapse={onCollapse} />
        ) : undefined
      }
    >
      <RecentBody recent={recent} />
    </ResultSection>
  )
}
