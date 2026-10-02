import { useTranslation } from "react-i18next"
import type { SearchWarning } from "@/entities/evidence/model"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export function WarningNote({ warnings }: { readonly warnings: readonly SearchWarning[] }) {
  const { t } = useTranslation("candidate")
  const codes = [...new Set(warnings.map((warning) => warning.code))]
  return (
    <div className={styles.note} role="note" aria-label={t("warning.title")}>
      <Icon name="warning" size="sm" tone="warning" />
      <div className={styles.body}>
        <p className={styles.title}>{t("warning.title")}</p>
        <ul className={styles.list}>
          {codes.map((code) => (
            <li key={code}>{t(`warning.${code}`)}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
