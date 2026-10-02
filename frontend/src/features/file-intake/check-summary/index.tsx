import { useTranslation } from "react-i18next"
import { FileProblem } from "@/entities/notice/file-problem"
import { IssueList } from "@/entities/notice/issue-list"
import type { CheckedFile, FileCheck } from "@/entities/notice/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { LoadingState } from "@/shared/ui/loading-state"
import { Bone } from "@/shared/ui/skeleton"
import { Tag } from "@/shared/ui/tag"
import { PreviewTable } from "../preview-table"
import styles from "./styles.module.css"

type AcceptedProps = {
  readonly check: CheckedFile
  readonly withFile: boolean
}

function Accepted({ check, withFile }: AcceptedProps) {
  const { t } = useTranslation("uploads")
  const { number } = useFormatters()
  const rejected = check.total - check.notices.length
  const stats = [
    { id: "total", label: t("dialog.total"), value: number(check.total), attention: false },
    {
      id: "valid",
      label: t("dialog.valid"),
      value: number(check.notices.length),
      attention: false,
    },
    {
      id: "invalid",
      label: t("dialog.invalid"),
      value: number(rejected),
      attention: rejected > 0,
    },
  ]
  return (
    <>
      {withFile ? (
        <p className={styles.file}>
          <Icon name="fileCheck" tone="confirmed" />
          {check.fileName}
        </p>
      ) : null}
      <dl className={styles.stats}>
        {stats.map((stat) => (
          <div
            key={stat.id}
            className={styles.stat}
            data-attention={stat.attention || undefined}
          >
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

export function CheckSkeleton({ label }: { readonly label: string }) {
  return (
    <LoadingState label={label}>
      <div className={styles.skeleton}>
        <Bone className={styles.boneFile} />
        <div className={styles.stats}>
          <Bone className={styles.boneStat} />
          <Bone className={styles.boneStat} />
          <Bone className={styles.boneStat} />
        </div>
        <Bone className={styles.boneBlock} />
      </div>
    </LoadingState>
  )
}

export type CheckSummaryProps = {
  readonly check: FileCheck
  readonly withFile?: boolean
}

export function CheckSummary({ check, withFile = true }: CheckSummaryProps) {
  return check.ok ? (
    <Accepted check={check} withFile={withFile} />
  ) : (
    <FileProblem check={check} />
  )
}
