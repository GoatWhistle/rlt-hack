import { useTranslation } from "react-i18next"
import { NavLink } from "react-router"
import {
  ANALYTICS_CATEGORIES_PATH,
  ANALYTICS_PATH,
  ANALYTICS_QUALITY_PATH,
  ANALYTICS_SOURCES_PATH,
} from "@/shared/config/paths"
import styles from "./styles.module.css"

const TABS = [
  { key: "overview", to: ANALYTICS_PATH, end: true },
  { key: "categories", to: ANALYTICS_CATEGORIES_PATH, end: false },
  { key: "quality", to: ANALYTICS_QUALITY_PATH, end: false },
  { key: "sources", to: ANALYTICS_SOURCES_PATH, end: false },
] as const

export type TabBarProps = { readonly search: string }

export function TabBar({ search }: TabBarProps) {
  const { t } = useTranslation("analytics")
  return (
    <nav className={styles.tabs} aria-label={t("tabs.legend")}>
      {TABS.map((tab) => (
        <NavLink
          key={tab.key}
          to={{ pathname: tab.to, search }}
          end={tab.end}
          className={styles.tab}
        >
          {t(`tabs.${tab.key}`)}
        </NavLink>
      ))}
    </nav>
  )
}
