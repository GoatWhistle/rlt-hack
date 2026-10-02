import { useTranslation } from "react-i18next"
import { useParams } from "react-router"
import { useSearchResult } from "@/entities/search/queries"
import { RecentPlaces } from "@/features/recent-places"
import { isApiError } from "@/shared/api/api-error"
import { SEARCH_PATH } from "@/shared/config/paths"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"
import { WorkspaceSkeleton } from "@/shared/ui/workspace-skeleton"
import { ResultView } from "../result-view"

export function SearchResultPage() {
  const { t } = useTranslation("search")
  const { t: common } = useTranslation()
  const { searchId = "" } = useParams()
  const result = useSearchResult(searchId)
  useDocumentTitle([result.data?.query.text, common("title.search")])

  if (result.isPending) return <WorkspaceSkeleton label={t("loading")} />
  if (result.isError) {
    if (isApiError(result.error) && result.error.status === 404) {
      return (
        <EmptyState
          icon="search"
          title={t("missing.title")}
          description={t("missing.text")}
          actions={<ButtonLink to={SEARCH_PATH}>{t("missing.action")}</ButtonLink>}
        >
          <RecentPlaces />
        </EmptyState>
      )
    }
    return <ErrorState error={result.error} headingLevel={1} onRetry={() => result.refetch()} />
  }
  return <ResultView key={result.data.searchId} result={result.data} />
}
