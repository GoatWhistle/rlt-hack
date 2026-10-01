import { useTranslation } from "react-i18next"
import { NavLink, Outlet } from "react-router"
import { LocaleSwitch } from "@/features/locale-switch"
import { Icon } from "@/shared/ui/icon"
import { SkipLink } from "@/shared/ui/skip-link"
import styles from "./styles.module.css"

export const MAIN_CONTENT_ID = "main-content"

export function AppShell() {
  const { t } = useTranslation()
  return (
    <div className={styles.shell}>
      <SkipLink targetId={MAIN_CONTENT_ID} label={t("app.skipToContent")} />
      <header className={styles.header}>
        <div className={styles.bar}>
          <NavLink to="/" className={styles.brand}>
            <span className={styles.mark}>
              <Icon name="logo" />
            </span>
            {t("app.name")}
          </NavLink>
          <nav aria-label={t("app.mainNavigation")} className={styles.nav}>
            <NavLink to="/" end className={styles.navLink}>
              {t("nav.home")}
            </NavLink>
          </nav>
          <LocaleSwitch />
        </div>
      </header>
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
