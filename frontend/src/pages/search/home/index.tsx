import { useEffect, useId, useRef } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router"
import { DEFAULT_REGION_CODE, isRegionCode } from "@/entities/evidence/regions"
import { SearchBox } from "@/features/search-box"
import { lotPath, SEARCH_TEXT_PARAM } from "@/shared/config/paths"
import { withViewTransition } from "@/shared/motion/view-transition"
import { useDocumentTitle } from "@/shared/routing/use-document-title"
import { PageTitle } from "@/shared/ui/page-title"
import { ReadingGuide } from "../reading-guide"
import { RecentList } from "../recent-list"
import { RecentReveal } from "../recent-toggle"
import styles from "./styles.module.css"
import { useRecentOpen } from "./use-recent-open"

function useToggleFocus(open: boolean, panelId: string) {
  const reveal = useRef<HTMLButtonElement>(null)
  const toggled = useRef(false)
  useEffect(() => {
    if (!toggled.current) return
    toggled.current = false
    if (!open) reveal.current?.focus()
    else document.getElementById(panelId)?.querySelector<HTMLElement>("h2[tabindex]")?.focus()
  }, [open, panelId])
  return { reveal, mark: () => (toggled.current = true) }
}

function regionFrom(param: string | null): string {
  if (param === "") return ""
  return param !== null && isRegionCode(param) ? param : DEFAULT_REGION_CODE
}

export function SearchPage() {
  const { t } = useTranslation("search")
  const { t: common } = useTranslation()
  useDocumentTitle(common("title.search"))
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const titleId = useId()
  const panelId = useId()
  const [open, setOpen] = useRecentOpen()
  const focus = useToggleFocus(open, panelId)
  const region = params.get("region")
  const draft = params.get(SEARCH_TEXT_PARAM) ?? ""
  const toggle = (next: boolean) => {
    focus.mark()
    withViewTransition("panel", () => setOpen(next))
  }
  return (
    <div className={styles.page} data-recent={open ? "open" : "closed"}>
      <section className={styles.search} aria-labelledby={titleId}>
        <div className={styles.head}>
          <div className={styles.intro}>
            <PageTitle id={titleId}>{t("home.title")}</PageTitle>
            <p className={styles.lead}>{t("home.lead")}</p>
          </div>
          <RecentReveal
            ref={focus.reveal}
            open={open}
            controls={panelId}
            onOpen={() => toggle(true)}
          />
        </div>
        <div className={styles.query}>
          <SearchBox
            key={draft}
            autoFocus
            shortcut
            initialText={draft}
            initialRegion={regionFrom(region)}
            onFound={(result) =>
              navigate(lotPath(result.id, "query"), { viewTransition: true })
            }
          />
        </div>
      </section>
      <div id={panelId} className={styles.recent}>
        <RecentList
          empty={<ReadingGuide />}
          controls={panelId}
          onCollapse={() => toggle(false)}
        />
      </div>
    </div>
  )
}
