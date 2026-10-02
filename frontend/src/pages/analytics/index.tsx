import { useTranslation } from "react-i18next"
import { Outlet } from "react-router"
import { useOverview } from "@/entities/analytics/queries"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { PageTitle } from "@/shared/ui/page-title"
import { ScopeBar } from "./scope-bar"
import styles from "./styles.module.css"
import { TabBar } from "./tab-bar"
import { useScope } from "./use-scope"

export { CategoriesPage } from "./categories"
export { OverviewPage } from "./overview"
export { QualityPage } from "./quality"
export { RecordsPage } from "./records"
export { SourcesPage } from "./sources"

export function AnalyticsLayout() {
  const { t } = useTranslation("analytics")
  useDocumentTitle(t("title"))
  const scope = useScope()
  const options = useOverview({})
  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <PageTitle>{t("title")}</PageTitle>
        <p className={styles.intro}>{t("intro")}</p>
      </header>
      <ScopeBar
        filters={scope.filters}
        sources={options.data?.sources ?? []}
        onChange={scope.change}
      />
      <TabBar search={scope.search} />
      <Outlet />
    </div>
  )
}
