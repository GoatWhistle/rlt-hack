import { useTranslation } from "react-i18next"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import type { RejectedFile } from "../model"
import styles from "./styles.module.css"

export function FileProblem({ check }: { readonly check: RejectedFile }) {
  const { t } = useTranslation("notices")
  const { list } = useFormatters()
  return (
    <div role="alert" className={styles.problem}>
      <Icon name="warning" tone="warning" />
      <div className={styles.text}>
        <h3 className={styles.title}>{t(`problem.${check.problem}.title`)}</h3>
        <p>
          {t(`problem.${check.problem}.text`, {
            columns: list(check.missing),
            limit: check.limit ?? 0,
          })}
        </p>
        <Caption>{check.fileName}</Caption>
      </div>
    </div>
  )
}
