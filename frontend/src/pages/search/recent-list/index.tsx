import type { ReactNode } from "react"
import { Trans, useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { SearchSummary } from "@/entities/search/model"
import { useRecentSearches } from "@/entities/search/queries"
import { searchPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { LoadingState } from "@/shared/ui/loading-state"
import { MetaChip, MetaChips } from "@/shared/ui/meta-chip"
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

function RecentFacts({ search }: { readonly search: SearchSummary }) {
  const { t } = useTranslation("search")
  const fact = (key: "items" | "candidates" | "recommended", count: number) => (
    <Trans t={t} i18nKey={`recent.${key}`} count={count} components={{ b: <b /> }} />
  )
  if (search.candidates === 0) {
    return (
      <MetaChips>
        <MetaChip tone="muted">{t("recent.none")}</MetaChip>
      </MetaChips>
    )
  }
  return (
    <MetaChips>
      <MetaChip>{fact("items", search.items)}</MetaChip>
      <MetaChip>{fact("candidates", search.candidates)}</MetaChip>
      {search.recommended > 0 ? (
        <MetaChip tone="accent">{fact("recommended", search.recommended)}</MetaChip>
      ) : null}
    </MetaChips>
  )
}

function RecentRow({ search }: { readonly search: SearchSummary }) {
  const { dateTime, time } = useFormatters()
  const today = isToday(search.createdAt)
  return (
    <Link to={searchPath(search.searchId)} className={styles.row}>
      <span className={styles.text}>{search.text}</span>
      <span className={styles.meta}>
        <RecentFacts search={search} />
        <time dateTime={search.createdAt}>
          {today ? time(search.createdAt) : dateTime(search.createdAt)}
        </time>
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
