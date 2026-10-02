import { useEffect, useId, useRef } from "react"
import { flushSync } from "react-dom"
import { useTranslation } from "react-i18next"
import { useNavigate, useSearchParams } from "react-router"
import { SearchBox } from "@/features/search-box"
import { SEARCH_TEXT_PARAM, searchPath } from "@/shared/config/paths"
import { prefersReducedMotion } from "@/shared/motion/settle-delay"
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

function withPanelTransition(change: () => void) {
  if (!("startViewTransition" in document) || prefersReducedMotion()) {
    change()
    return
  }
  const root = document.documentElement
  root.dataset.transition = "panel"
  const transition = document.startViewTransition(() => flushSync(change))
  void transition.finished.finally(() => {
    delete root.dataset.transition
  })
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
  const draft = params.get(SEARCH_TEXT_PARAM) ?? ""
  const toggle = (next: boolean) => {
    focus.mark()
    withPanelTransition(() => setOpen(next))
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
        <SearchBox
          key={draft}
          autoFocus
          shortcut
          initialText={draft}
          onFound={(result) => navigate(searchPath(result.searchId), { viewTransition: true })}
        />
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
