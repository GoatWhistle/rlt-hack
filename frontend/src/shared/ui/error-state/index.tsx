import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { describeError } from "@/shared/errors/describe-error"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { Button } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"

export type ErrorStateProps = {
  readonly error: unknown
  readonly title?: string
  readonly onRetry?: () => void
  readonly extraAction?: ReactNode
  readonly headingLevel?: 1 | 2
}

export function ErrorState({
  error,
  title,
  onRetry,
  extraAction,
  headingLevel = 2,
}: ErrorStateProps) {
  const { t } = useTranslation()
  const errorMessage = useErrorMessage()
  const { code } = describeError(error)
  const retry = onRetry ? <Button onClick={onRetry}>{t("action.retry")}</Button> : null
  return (
    <EmptyState
      tone="error"
      headingLevel={headingLevel}
      title={title ?? t("routeError.title")}
      description={errorMessage(error)}
      details={code ? t("errorDetails.code", { code }) : undefined}
      actions={
        retry || extraAction ? (
          <>
            {retry}
            {extraAction}
          </>
        ) : undefined
      }
    />
  )
}
