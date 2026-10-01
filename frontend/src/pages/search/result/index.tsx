import { useTranslation } from "react-i18next"
import { useParams } from "react-router"
import { useSearchResult } from "@/entities/search/queries"
import { isApiError } from "@/shared/api/api-error"
import { SEARCH_PATH } from "@/shared/config/paths"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { WorkspaceSkeleton } from "@/shared/ui/workspace-skeleton"
import { ResultHeader } from "../result-header"
import { SearchWorkspace } from "../search-workspace"
import { WarningNote } from "../warning-note"
import styles from "./styles.module.css"

export function SearchResultPage() {
  const { t } = useTranslation("search")
  const { searchId = "" } = useParams()
  const result = useSearchResult(searchId)

  if (result.isPending) return <WorkspaceSkeleton label={t("loading")} />
  if (result.isError) {
    if (isApiError(result.error) && result.error.status === 404) {
      return (
        <EmptyState
          icon="search"
          title={t("missing.title")}
          description={t("missing.text")}
          actions={<ButtonLink to={SEARCH_PATH}>{t("missing.action")}</ButtonLink>}
        />
      )
    }
    return <ErrorState error={result.error} headingLevel={1} onRetry={() => result.refetch()} />
  }

  const data = result.data
  return (
    <div className={styles.page}>
      <ResultHeader result={data} />
      {data.warnings.length > 0 ? <WarningNote warnings={data.warnings} /> : null}
      <SearchWorkspace key={data.searchId} result={data} />
    </div>
  )
}
