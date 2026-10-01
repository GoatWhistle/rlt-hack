import { useCallback } from "react"
import { useTranslation } from "react-i18next"
import { describeError } from "./describe-error"

export function useErrorMessage(): (error: unknown) => string {
  const { t } = useTranslation("errors")
  return useCallback((error: unknown) => t(describeError(error).messageKey), [t])
}
