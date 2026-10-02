import { useTranslation } from "react-i18next"
import { RecentPlaces } from "@/features/recent-places"
import { HISTORY_PATH, SEARCH_PATH } from "@/shared/config/paths"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { Icon } from "@/shared/ui/icon"

export function NotFoundPage() {
  const { t } = useTranslation()
  useDocumentTitle(t("title.notFound"))
  return (
    <EmptyState
      icon="compass"
      title={t("notFound.title")}
      description={t("notFound.description")}
      actions={
        <>
          <ButtonLink to={SEARCH_PATH}>
            <Icon name="search" />
            {t("action.newSearch")}
          </ButtonLink>
          <ButtonLink to={HISTORY_PATH} variant="secondary">
            {t("action.home")}
          </ButtonLink>
        </>
      }
    >
      <RecentPlaces />
    </EmptyState>
  )
}
