import { useEffect } from "react"
import { useTranslation } from "react-i18next"

export function useDocumentTitle(parts: readonly (string | undefined)[]): void {
  const { t } = useTranslation()
  const title = [...parts.filter((part): part is string => Boolean(part)), t("app.name")].join(
    t("title.separator"),
  )
  useEffect(() => {
    document.title = title
  }, [title])
}
