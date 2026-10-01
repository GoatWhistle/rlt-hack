import { useTranslation } from "react-i18next"
import { Link, Outlet, ScrollRestoration } from "react-router"
import { NavTabs } from "@/app/nav-tabs"
import { LocaleSwitch } from "@/features/locale-switch"
import { REPOSITORY_URL } from "@/shared/config/links"
import { UPLOADS_PATH } from "@/shared/config/paths"
import { BrandMark } from "@/shared/ui/brand-mark"
import { GithubMark } from "@/shared/ui/github-mark"
import { SkipLink } from "@/shared/ui/skip-link"
import { ToolLink } from "@/shared/ui/tool-button"
import styles from "./styles.module.css"

export const MAIN_CONTENT_ID = "main-content"

export function AppShell() {
  const { t } = useTranslation()
  return (
    <div className={styles.shell}>
      <SkipLink targetId={MAIN_CONTENT_ID} label={t("app.skipToContent")} />
      <header className={styles.header}>
        <div className={styles.bar}>
          <Link to={UPLOADS_PATH} className={styles.brand}>
            <BrandMark />
            <span className={styles.wordmark}>{t("app.name")}</span>
          </Link>
          <NavTabs />
          <div className={styles.tools}>
            <LocaleSwitch />
            <ToolLink
              href={REPOSITORY_URL}
              aria-label={t("app.repository")}
              title={t("app.repository")}
            >
              <GithubMark />
            </ToolLink>
          </div>
        </div>
      </header>
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className={styles.main}>
        <Outlet />
      </main>
      <ScrollRestoration />
    </div>
  )
}
