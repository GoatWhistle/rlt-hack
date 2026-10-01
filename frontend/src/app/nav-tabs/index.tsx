import { type CSSProperties, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Link, useMatch } from "react-router"
import { LOTS_ENTRY_PATH, SEARCH_PATH, UPLOADS_PATH } from "@/shared/config/paths"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"
import { useIndicator } from "./use-indicator"

type TabKey = "uploads" | "lots" | "search"

function useActiveTab(): TabKey | null {
  const atUploads = useMatch(UPLOADS_PATH)
  const insideUpload = useMatch(`${UPLOADS_PATH}/:uploadId/*`)
  const atEntry = useMatch(LOTS_ENTRY_PATH)
  const atSearch = useMatch(`${SEARCH_PATH}/*`)
  if (atUploads) return "uploads"
  if (insideUpload || atEntry) return "lots"
  if (atSearch) return "search"
  return null
}

export function NavTabs() {
  const { t } = useTranslation()
  const ref = useRef<HTMLElement>(null)
  const active = useActiveTab()
  const box = useIndicator(ref, active)
  const tabs: readonly { key: TabKey; to: string; label: string; icon: IconName }[] = [
    { key: "uploads", to: UPLOADS_PATH, label: t("nav.uploads"), icon: "upload" },
    { key: "lots", to: LOTS_ENTRY_PATH, label: t("nav.lots"), icon: "fileCheck" },
    { key: "search", to: SEARCH_PATH, label: t("nav.search"), icon: "search" },
  ]
  const position = box
    ? ({
        "--indicator-x": `${box.x}px`,
        "--indicator-width": `${box.width}px`,
      } as CSSProperties)
    : undefined

  return (
    <nav ref={ref} aria-label={t("app.mainNavigation")} className={styles.nav} style={position}>
      {tabs.map((tab) => (
        <Link
          key={tab.key}
          to={tab.to}
          aria-current={tab.key === active ? "page" : undefined}
          aria-label={tab.label}
          className={styles.tab}
        >
          <span className={styles.icon}>
            <Icon name={tab.icon} />
          </span>
          <span className={styles.label}>{tab.label}</span>
        </Link>
      ))}
      {box ? <span aria-hidden="true" className={styles.indicator} /> : null}
    </nav>
  )
}
