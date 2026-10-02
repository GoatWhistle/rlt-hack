import { type CSSProperties, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Link, type Location, matchPath, useLocation, useNavigation } from "react-router"
import { TEXT_QUERY_LOT } from "@/entities/upload/model"
import {
  ANALYTICS_PATH,
  HISTORY_PATH,
  LOTS_ENTRY_PATH,
  SEARCH_PATH,
  UPLOADS_PATH,
} from "@/shared/config/paths"
import { Icon, type IconName } from "@/shared/ui/icon"
import { preload, type RouteModule } from "../route-modules"
import styles from "./styles.module.css"
import { useIndicator } from "./use-indicator"

type TabKey = "search" | "history" | "analytics"

export function tabOf(pathname: string): TabKey | null {
  if (matchPath(`${SEARCH_PATH}/*`, pathname)) return "search"
  if (matchPath(`${UPLOADS_PATH}/:uploadId/lots/${TEXT_QUERY_LOT}`, pathname)) return "search"
  if (
    matchPath(HISTORY_PATH, pathname) ||
    matchPath(`${UPLOADS_PATH}/*`, pathname) ||
    matchPath(LOTS_ENTRY_PATH, pathname)
  )
    return "history"
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
  { key: "history", to: HISTORY_PATH, icon: "clock", module: "history" },
  { key: "analytics", to: ANALYTICS_PATH, icon: "chart", module: "analytics" },
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
