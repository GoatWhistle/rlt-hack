import { useTranslation } from "react-i18next"
import { UPLOADS_PATH } from "@/shared/config/paths"
import { ButtonLink } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"

export function LotsEntryPage() {
  const { t } = useTranslation("lots")
  return (
    <EmptyState
      title={t("entry.title")}
      description={t("entry.text")}
      actions={<ButtonLink to={UPLOADS_PATH}>{t("entry.action")}</ButtonLink>}
    />
  )
}
