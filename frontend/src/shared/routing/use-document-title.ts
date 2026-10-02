import { useEffect } from "react"
import { useTranslation } from "react-i18next"

export function useDocumentTitle(page?: string): void {
  const { t } = useTranslation()
  const app = t("app.name")
  const title = page ? `${app}${t("title.separator")}${page}` : app
  useEffect(() => {
    document.title = title
  }, [title])
}
