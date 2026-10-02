import { useId } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router"
import { SearchBox } from "@/features/search-box"
import { SEARCH_TEXT_PARAM, searchPath } from "@/shared/config/paths"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { PageTitle } from "@/shared/ui/page-title"
import { ReadingGuide } from "../reading-guide"
import { RecentList } from "../recent-list"
import styles from "./styles.module.css"

export function SearchPage() {
  const { t } = useTranslation("search")
  const { t: common } = useTranslation()
  useDocumentTitle(common("title.search"))
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const titleId = useId()
  const draft = params.get(SEARCH_TEXT_PARAM) ?? ""
  return (
    <div className={styles.page}>
      <section className={styles.search} aria-labelledby={titleId}>
        <div className={styles.head}>
          <PageTitle id={titleId}>{t("home.title")}</PageTitle>
          <p className={styles.lead}>{t("home.lead")}</p>
        </div>
        <SearchBox
          key={draft}
          autoFocus
          shortcut
          initialText={draft}
          onFound={(result) => navigate(searchPath(result.searchId), { viewTransition: true })}
        />
      </section>
      <RecentList empty={<ReadingGuide />} />
    </div>
  )
}
