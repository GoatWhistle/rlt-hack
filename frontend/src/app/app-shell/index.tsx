import { useTranslation } from "react-i18next"
import { Link, NavLink, Outlet, ScrollRestoration, useMatch } from "react-router"
import { LocaleSwitch } from "@/features/locale-switch"
import { LOTS_ENTRY_PATH, UPLOADS_PATH } from "@/shared/config/paths"
import { Icon } from "@/shared/ui/icon"
import { SkipLink } from "@/shared/ui/skip-link"
import styles from "./styles.module.css"

export const MAIN_CONTENT_ID = "main-content"

export function AppShell() {
  const { t } = useTranslation()
  const insideUpload = useMatch(`${UPLOADS_PATH}/:uploadId/*`)
  const atEntry = useMatch(LOTS_ENTRY_PATH)
  const lotsActive = insideUpload !== null || atEntry !== null
  return (
    <div className={styles.shell}>
      <SkipLink targetId={MAIN_CONTENT_ID} label={t("app.skipToContent")} />
      <header className={styles.header}>
        <div className={styles.bar}>
          <Link to={UPLOADS_PATH} className={styles.brand}>
            <span className={styles.mark}>
              <Icon name="logo" />
            </span>
            {t("app.name")}
          </Link>
          <nav aria-label={t("app.mainNavigation")} className={styles.nav}>
            <NavLink to={UPLOADS_PATH} end className={styles.navLink}>
              {t("nav.uploads")}
            </NavLink>
            <Link
              to={LOTS_ENTRY_PATH}
              aria-current={lotsActive ? "page" : undefined}
              className={styles.navLink}
            >
              {t("nav.lots")}
            </Link>
          </nav>
          <LocaleSwitch />
        </div>
      </header>
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
      <ScrollRestoration />
    </div>
  )
}
