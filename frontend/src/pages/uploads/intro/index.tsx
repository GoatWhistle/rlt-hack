import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { SEARCH_PATH } from "@/shared/config/paths"
import { Icon } from "@/shared/ui/icon"
import { PageTitle } from "@/shared/ui/page-title"
import { Dropzone } from "../dropzone"
import { FormatHelp } from "../format-help"
import styles from "./styles.module.css"

export function Intro({ onFile }: { readonly onFile: (file: File) => void }) {
  const { t } = useTranslation("uploads")
  return (
    <div className={styles.intro}>
      <header className={styles.head}>
        <PageTitle className={styles.title}>{t("intro.title")}</PageTitle>
        <p className={styles.lead}>{t("intro.text")}</p>
      </header>
      <div className={styles.drop}>
        <Dropzone onSelect={onFile} />
        <p className={styles.privacy}>
          <Icon name="lock" size="sm" />
          {t("intro.privacy")}
        </p>
        <Link to={SEARCH_PATH} className={styles.alternative}>
          <Icon name="search" size="sm" />
          {t("intro.searchInstead")}
        </Link>
      </div>
      <div className={styles.format}>
        <FormatHelp />
      </div>
    </div>
  )
}
