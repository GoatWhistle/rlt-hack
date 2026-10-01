import { useTranslation } from "react-i18next"
import { NavLink, Outlet } from "react-router"
import { LocaleSwitch } from "@/features/locale-switch"
import { SkipLink } from "@/shared/ui/skip-link"
import styles from "./styles.module.css"

export const MAIN_CONTENT_ID = "main-content"

export function AppShell() {
  const { t } = useTranslation()
  return (
    <div className={styles.shell}>
      <SkipLink targetId={MAIN_CONTENT_ID} label={t("app.skipToContent")} />
      <header className={styles.header}>
        <NavLink to="/" className={styles.brand}>
          {t("app.name")}
        </NavLink>
        <nav aria-label={t("app.mainNavigation")} className={styles.nav}>
          <NavLink to="/" end className={styles.navLink}>
            {t("nav.home")}
          </NavLink>
        </nav>
        <LocaleSwitch />
      </header>
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
