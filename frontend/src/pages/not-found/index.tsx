import { useTranslation } from "react-i18next"
import { useLocation, useNavigate } from "react-router"
import { LOTS_ENTRY_PATH } from "@/shared/config/paths"
import { Button, ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"

export function NotFoundPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const canGoBack = location.key !== "default"
  return (
    <EmptyState
      icon="compass"
      title={t("notFound.title")}
      description={t("notFound.description")}
      details={t("errorDetails.code", { code: "http_404" })}
      actions={
        <>
          <ButtonLink to="/">{t("action.home")}</ButtonLink>
          {canGoBack ? (
            <Button variant="secondary" onClick={() => navigate(-1)}>
              {t("action.back")}
            </Button>
          ) : (
            <ButtonLink to={LOTS_ENTRY_PATH} variant="secondary">
              {t("action.lots")}
            </ButtonLink>
          )}
        </>
      }
    />
  )
}
