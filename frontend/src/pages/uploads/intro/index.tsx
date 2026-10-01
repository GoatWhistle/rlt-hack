import { useTranslation } from "react-i18next"
import { KNOWN_COLUMNS, REQUIRED_COLUMNS } from "@/entities/notice/model"
import { Icon } from "@/shared/ui/icon"
import { Dropzone } from "../dropzone"
import styles from "./styles.module.css"

export const SAMPLE_PATH = "/notices-sample.csv"

const OPTIONAL_COLUMNS = KNOWN_COLUMNS.filter(
  (column) => !(REQUIRED_COLUMNS as readonly string[]).includes(column),
)

export function Intro({ onFile }: { readonly onFile: (file: File) => void }) {
  const { t } = useTranslation("uploads")
  return (
    <div className={styles.intro}>
      <div className={styles.text}>
        <h1 className={styles.title}>{t("intro.title")}</h1>
        <p className={styles.lead}>{t("intro.text")}</p>
        <section className={styles.format} aria-labelledby="format-title">
          <h2 id="format-title" className={styles.formatTitle}>
            {t("intro.format")}
          </h2>
          <p className={styles.formatText}>{t("intro.formatText")}</p>
          <dl className={styles.columns}>
            <dt>{t("intro.required")}</dt>
            <dd className={styles.codes}>{REQUIRED_COLUMNS.join(", ")}</dd>
            <dt>{t("intro.optional")}</dt>
            <dd className={styles.codes}>{OPTIONAL_COLUMNS.join(", ")}</dd>
          </dl>
          <a href={SAMPLE_PATH} download className={styles.sample}>
            <Icon name="download" />
            {t("intro.sample")}
          </a>
        </section>
      </div>
      <div className={styles.card}>
        <Dropzone onSelect={onFile} />
        <p className={styles.privacy}>
          <Icon name="lock" size="sm" />
          {t("intro.privacy")}
        </p>
      </div>
    </div>
  )
}
