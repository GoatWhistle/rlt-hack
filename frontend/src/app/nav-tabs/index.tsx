import { type CSSProperties, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Link, type Location, matchPath, useLocation, useNavigation } from "react-router"
import {
  ANALYTICS_PATH,
  LOTS_ENTRY_PATH,
  SEARCH_PATH,
  UPLOADS_PATH,
} from "@/shared/config/paths"
import { Icon, type IconName } from "@/shared/ui/icon"
import { preload, type RouteModule } from "../route-modules"
import styles from "./styles.module.css"
import { useIndicator } from "./use-indicator"

type TabKey = "search" | "uploads" | "lots" | "analytics"

export function tabOf(pathname: string): TabKey | null {
  if (matchPath(UPLOADS_PATH, pathname)) return "uploads"
  if (
    matchPath(`${UPLOADS_PATH}/:uploadId/*`, pathname) ||
    matchPath(LOTS_ENTRY_PATH, pathname)
  )
    return "lots"
  if (matchPath(`${SEARCH_PATH}/*`, pathname)) return "search"
  if (matchPath(`${ANALYTICS_PATH}/*`, pathname)) return "analytics"
  return null
}

function useActiveTab(): TabKey | null {
  const location = useLocation()
  const navigation = useNavigation()
  const target: Location | undefined = navigation.location
  return tabOf((target ?? location).pathname)
}

const TABS: readonly { key: TabKey; to: string; icon: IconName; module: RouteModule }[] = [
  { key: "search", to: SEARCH_PATH, icon: "search", module: "search" },
  { key: "uploads", to: UPLOADS_PATH, icon: "upload", module: "uploads" },
  { key: "lots", to: LOTS_ENTRY_PATH, icon: "fileCheck", module: "lots" },
  { key: "analytics", to: ANALYTICS_PATH, icon: "wave", module: "analytics" },
]

export function NavTabs() {
  const { t } = useTranslation()
  const ref = useRef<HTMLElement>(null)
  const active = useActiveTab()
  const { box, animated } = useIndicator(ref, active)
  const position = box
    ? ({
        "--indicator-x": `${box.x}px`,
        "--indicator-scale": String(box.width),
      } as CSSProperties)
    : undefined

  return (
    <nav
      ref={ref}
      aria-label={t("app.mainNavigation")}
      className={styles.nav}
      style={position}
      data-indicator={animated ? "ready" : undefined}
    >
      {TABS.map((tab) => {
        const label = t(`nav.${tab.key}`)
        return (
          <Link
            key={tab.key}
            to={tab.to}
            aria-current={tab.key === active ? "page" : undefined}
            aria-label={label}
            className={styles.tab}
            onPointerEnter={() => preload(tab.module)}
            onFocus={() => preload(tab.module)}
          >
            <span className={styles.icon}>
              <Icon name={tab.icon} />
            </span>
            <span className={styles.label}>{label}</span>
          </Link>
        )
      })}
      {box ? <span aria-hidden="true" className={styles.indicator} /> : null}
    </nav>
  )
}
