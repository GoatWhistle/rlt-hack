import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import type { SearchSummary } from "@/entities/search/model"
import { useRecentSearches } from "@/entities/search/queries"
import { searchPath } from "@/shared/config/paths"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon } from "@/shared/ui/icon"
import { LoadingState } from "@/shared/ui/loading-state"
import { ResultSection } from "@/shared/ui/result-section"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

function RecentRow({ search }: { readonly search: SearchSummary }) {
  const { t } = useTranslation("search")
  const { dateTime } = useFormatters()
  const facts = [
    t("recent.items", { count: search.items }),
    t("recent.candidates", { count: search.candidates }),
    ...(search.recommended > 0 ? [t("recent.recommended", { count: search.recommended })] : []),
  ]
  return (
    <Link to={searchPath(search.searchId)} className={styles.row}>
      <span className={styles.text}>{search.text}</span>
      <span className={styles.meta}>
        <span>{facts.join(" · ")}</span>
        <time dateTime={search.createdAt}>{dateTime(search.createdAt)}</time>
      </span>
      <span className={styles.chevron} aria-hidden="true">
        <Icon name="chevron" size="sm" />
      </span>
    </Link>
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
  return (
    <ul className={styles.list}>
      {recent.data.map((search) => (
        <li key={search.searchId}>
          <RecentRow search={search} />
        </li>
      ))}
    </ul>
  )
}

export function RecentList({ empty }: { readonly empty: ReactNode }) {
  const { t } = useTranslation("search")
  const recent = useRecentSearches()
  if (recent.isSuccess && recent.data.length === 0) return empty
  return (
    <ResultSection framed title={t("recent.title")}>
      <RecentBody recent={recent} />
    </ResultSection>
  )
}
