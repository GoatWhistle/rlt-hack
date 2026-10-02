import { useTranslation } from "react-i18next"
import { useRevalidator, useRouteError } from "react-router"
import { NotFoundPage } from "@/pages/not-found"
import { UPLOADS_PATH } from "@/shared/config/paths"
import { describeError } from "@/shared/errors/describe-error"
import { reloadPage } from "@/shared/errors/reload-page"
import { Button, ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { ErrorState } from "@/shared/ui/error-state"

export type RouteErrorPageProps = {
  readonly onReload?: () => void
}

export function RouteErrorPage({ onReload = reloadPage }: RouteErrorPageProps) {
  const { t } = useTranslation()
  const error = useRouteError()
  const revalidator = useRevalidator()
  const { kind } = describeError(error)

  if (kind === "notFound") return <NotFoundPage />

  if (kind === "updateRequired") {
    return (
      <EmptyState
        tone="error"
        title={t("updateRequired.title")}
        description={t("updateRequired.description")}
        actions={<Button onClick={onReload}>{t("action.reload")}</Button>}
      />
    )
  }

  return (
    <ErrorState
      error={error}
      headingLevel={1}
      onRetry={() => void revalidator.revalidate()}
      extraAction={
        <ButtonLink variant="secondary" to={UPLOADS_PATH}>
          {t("action.home")}
        </ButtonLink>
      }
    />
  )
}
