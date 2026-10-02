import type { ReactNode } from "react"
import { Trans, useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { SearchSummary } from "@/entities/search/model"
import { useSearchHistory } from "@/entities/search/queries"
import { searchPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { LoadingState } from "@/shared/ui/loading-state"
import { MetaChip, MetaChips } from "@/shared/ui/meta-chip"
import { ResultSection } from "@/shared/ui/result-section"
import { TextButton } from "@/shared/ui/text-button"
import { RecentCollapse } from "../recent-toggle"
import { groupHistory, type HistoryAge, isRecentDay } from "./history-groups"
import styles from "./styles.module.css"

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

function RecentRow({
  search,
  age,
}: {
  readonly search: SearchSummary
  readonly age: HistoryAge
}) {
  const { dateTime, time } = useFormatters()
  const today = isRecentDay(age)
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
  age,
  searches,
}: {
  readonly age: HistoryAge
  readonly searches: readonly SearchSummary[]
}) {
  const { relative } = useFormatters()
  const title = relative(age.value, age.unit)
  return (
    <li className={styles.group}>
      <h3 className={styles.groupTitle}>{title}</h3>
      <ul className={styles.list}>
        {searches.map((search) => (
          <li key={search.searchId}>
            <RecentRow search={search} age={age} />
          </li>
        ))}
      </ul>
    </li>
  )
}

function RecentBody({ recent }: { readonly recent: ReturnType<typeof useSearchHistory> }) {
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
  const searches = recent.data.pages.flatMap((page) => page.searches)
  const total = recent.data.pages[0]?.total ?? searches.length
  return (
    <div className={styles.scroll}>
      <ul className={styles.groups}>
        {groupHistory(searches).map((group) => (
          <RecentGroup key={group.key} age={group.age} searches={group.searches} />
        ))}
      </ul>
      {recent.hasNextPage ? (
        <div className={styles.more}>
          <TextButton
            aria-busy={recent.isFetchingNextPage || undefined}
            disabled={recent.isFetchingNextPage}
            onClick={() => recent.fetchNextPage()}
          >
            {t("recent.more", { count: Math.max(total - searches.length, 0) })}
          </TextButton>
        </div>
      ) : null}
    </div>
  )
}

export type RecentListProps = {
  readonly empty: ReactNode
  readonly controls?: string
  readonly onCollapse?: () => void
}

export function RecentList({ empty, controls, onCollapse }: RecentListProps) {
  const { t } = useTranslation("search")
  const recent = useSearchHistory()
  if (recent.isSuccess && recent.data.pages[0]?.searches.length === 0) return empty
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
