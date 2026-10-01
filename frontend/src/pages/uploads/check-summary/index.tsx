import { useTranslation } from "react-i18next"
import { FileProblem } from "@/entities/notice/file-problem"
import { IssueList } from "@/entities/notice/issue-list"
import type { CheckedFile, FileCheck } from "@/entities/notice/model"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { Tag } from "@/shared/ui/tag"
import { PreviewTable } from "../preview-table"
import styles from "./styles.module.css"

function Accepted({ check }: { readonly check: CheckedFile }) {
  const { t } = useTranslation("uploads")
  const rejected = check.total - check.notices.length
  const stats = [
    { id: "total", label: t("dialog.total"), value: check.total },
    { id: "valid", label: t("dialog.valid"), value: check.notices.length },
    { id: "invalid", label: t("dialog.invalid"), value: rejected },
  ]
  return (
    <>
      <p className={styles.file}>
        <Icon name="fileCheck" tone="confirmed" />
        {check.fileName}
      </p>
      <dl className={styles.stats}>
        {stats.map((stat) => (
          <div key={stat.id} className={styles.stat}>
            <dt className={styles.statLabel}>{stat.label}</dt>
            <dd className={styles.statValue}>{stat.value}</dd>
          </div>
        ))}
      </dl>
      {check.notices.length === 0 ? (
        <p role="alert" className={styles.alert}>
          {t("dialog.noValid")}
        </p>
      ) : null}
      <section className={styles.section} aria-labelledby="check-columns">
        <h3 id="check-columns" className={styles.heading}>
          {t("dialog.columns")}
        </h3>
        <ul className={styles.columns}>
          {check.columns.map((column) => (
            <Tag key={column.name} as="li" tone={column.known ? "solid" : "tentative"}>
              {column.known ? <Icon name="check" size="sm" tone="confirmed" /> : null}
              {column.known ? column.name : t("dialog.unknownColumn", { name: column.name })}
            </Tag>
          ))}
        </ul>
      </section>
      <section className={styles.section} aria-labelledby="check-preview">
        <h3 id="check-preview" className={styles.heading}>
          {t("dialog.preview", { count: check.preview.length, total: check.total })}
        </h3>
        <PreviewTable columns={check.columns} rows={check.preview} />
      </section>
      {check.issues.length > 0 ? (
        <section className={styles.section} aria-labelledby="check-issues">
          <h3 id="check-issues" className={styles.heading}>
            {t("dialog.issues", { count: rejected })}
          </h3>
          <Caption>{t("dialog.issuesNote")}</Caption>
          <IssueList issues={check.issues} />
        </section>
      ) : null}
    </>
  )
}

export function CheckSummary({ check }: { readonly check: FileCheck }) {
  return check.ok ? <Accepted check={check} /> : <FileProblem check={check} />
}
