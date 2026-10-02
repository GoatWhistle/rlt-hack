import { useTranslation } from "react-i18next"
import { FileProblem } from "@/entities/notice/file-problem"
import { Icon } from "@/shared/ui/icon"
import { CheckSummary } from "../check-summary"
import type { Intake } from "../model"
import styles from "./styles.module.css"

export function CheckDisclosure({ intake }: { readonly intake: Intake | null }) {
  const { t } = useTranslation("uploads")
  if (intake?.status !== "checked") return null
  const { check } = intake
  if (!check.ok) return <FileProblem check={check} />
  const rejected = check.total - check.notices.length
  return (
    <details className={styles.disclosure}>
      <summary className={styles.summary}>
        <Icon name="fileCheck" tone={check.notices.length > 0 ? "confirmed" : "warning"} />
        <span className={styles.facts}>
          <span className={styles.lots}>
            {t("intake.lots", { count: check.notices.length })}
          </span>
          {rejected > 0 ? (
            <span className={styles.issues}>{t("intake.issues", { count: rejected })}</span>
          ) : null}
        </span>
        <span className={styles.more}>
          {t("intake.details")}
          <span className={styles.chevron} aria-hidden="true">
            <Icon name="chevron" size="sm" />
          </span>
        </span>
      </summary>
      <div className={styles.content}>
        <CheckSummary check={check} withFile={false} />
      </div>
    </details>
  )
}
