import { useId } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router"
import { useSearchGateway } from "@/entities/search/gateway-context"
import { SearchBox } from "@/features/search-box"
import { SEARCH_TEXT_PARAM, searchPath } from "@/shared/config/paths"
import { Caption } from "@/shared/ui/caption"
import { RecentList } from "../recent-list"
import styles from "./styles.module.css"

export function SearchPage() {
  const { t } = useTranslation("search")
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const gateway = useSearchGateway()
  const titleId = useId()
  const draft = params.get(SEARCH_TEXT_PARAM) ?? ""
  return (
    <div className={styles.page}>
      <section className={styles.search} aria-labelledby={titleId}>
        <div className={styles.head}>
          <h1 id={titleId} className={styles.title}>
            {t("home.title")}
          </h1>
          <p className={styles.lead}>{t("home.lead")}</p>
        </div>
        <SearchBox
          key={draft}
          initialText={draft}
          onFound={(result) => navigate(searchPath(result.searchId))}
        />
        {gateway.demo ? <Caption muted>{t("demoNote")}</Caption> : null}
      </section>
      <RecentList />
    </div>
  )
}
