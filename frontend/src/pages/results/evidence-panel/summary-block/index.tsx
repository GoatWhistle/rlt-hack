import { useTranslation } from "react-i18next"
import type { Company } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { Block } from "../block"
import styles from "./styles.module.css"

export function SummaryBlock({ company }: { readonly company: Company }) {
  const { t } = useTranslation()
  const recommended = company.status === "recommended"
  const main = company.clarify[0]
  return (
    <Block
      title={
        recommended ? t("results.evidence.summaryTitle") : t("results.evidence.checkTitle")
      }
      icon={recommended ? "checkCircle" : "warning"}
      tone={recommended ? "confirmed" : "current"}
    >
      <p className={styles.summary}>{company.summary}</p>
      {main ? (
        <p className={styles.clarify}>
          <Icon name="warning" size="sm" />
          <span>
            <strong className={styles.label}>{t("results.evidence.mainClarify")}</strong>
            {main}
          </span>
        </p>
      ) : null}
    </Block>
  )
}
