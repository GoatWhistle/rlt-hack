import { type CSSProperties, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Link, useMatch } from "react-router"
import { LOTS_ENTRY_PATH, UPLOADS_PATH } from "@/shared/config/paths"
import styles from "./styles.module.css"
import { useIndicator } from "./use-indicator"

type TabKey = "uploads" | "lots"

function useActiveTab(): TabKey | null {
  const atUploads = useMatch(UPLOADS_PATH)
  const insideUpload = useMatch(`${UPLOADS_PATH}/:uploadId/*`)
  const atEntry = useMatch(LOTS_ENTRY_PATH)
  if (atUploads) return "uploads"
  if (insideUpload || atEntry) return "lots"
  return null
}

export function NavTabs() {
  const { t } = useTranslation()
  const ref = useRef<HTMLElement>(null)
  const active = useActiveTab()
  const box = useIndicator(ref, active)
  const tabs: readonly { key: TabKey; to: string; label: string }[] = [
    { key: "uploads", to: UPLOADS_PATH, label: t("nav.uploads") },
    { key: "lots", to: LOTS_ENTRY_PATH, label: t("nav.lots") },
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
          className={styles.tab}
        >
          {tab.label}
        </Link>
      ))}
      {box ? <span aria-hidden="true" className={styles.indicator} /> : null}
    </nav>
  )
}
