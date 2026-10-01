import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import { Dropzone } from "../dropzone"
import { FormatHelp } from "../format-help"
import styles from "./styles.module.css"

export function Intro({ onFile }: { readonly onFile: (file: File) => void }) {
  const { t } = useTranslation("uploads")
  return (
    <div className={styles.intro}>
      <header className={styles.head}>
        <h1 className={styles.title}>{t("intro.title")}</h1>
        <p className={styles.lead}>{t("intro.text")}</p>
      </header>
      <div className={styles.drop}>
        <Dropzone onSelect={onFile} />
        <p className={styles.privacy}>
          <Icon name="lock" size="sm" />
          {t("intro.privacy")}
        </p>
      </div>
      <div className={styles.format}>
        <FormatHelp />
      </div>
    </div>
  )
}
