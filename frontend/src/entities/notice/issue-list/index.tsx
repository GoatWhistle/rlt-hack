import { useTranslation } from "react-i18next"
import { CollapsibleList } from "@/shared/ui/collapsible-list"
import type { RowIssue } from "../model"
import styles from "./styles.module.css"

export const ISSUE_LIMIT = 5

export function IssueList({ issues }: { readonly issues: readonly RowIssue[] }) {
  const { t } = useTranslation("notices")
  return (
    <CollapsibleList
      items={issues}
      limit={ISSUE_LIMIT}
      itemKey={(issue) => `${issue.row}:${issue.code}`}
      renderItem={(issue) => (
        <span className={styles.issue}>
          <span className={styles.row}>{t("row", { row: issue.row })}</span>
          <span>{t(`issue.${issue.code}`, { value: issue.value ?? "" })}</span>
        </span>
      )}
    />
  )
}
