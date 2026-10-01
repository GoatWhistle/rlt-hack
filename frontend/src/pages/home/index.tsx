import { useTranslation } from "react-i18next"
import { EmptyState } from "@/shared/ui/empty-state"

export function HomePage() {
  const { t } = useTranslation()
  return <EmptyState title={t("home.title")} description={t("home.description")} />
}
