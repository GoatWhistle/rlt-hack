import { Trans, useTranslation } from "react-i18next"
import { Link } from "react-router"
import { isProcessing, TEXT_QUERY_LOT, type UploadSummary } from "@/entities/upload/model"
import { lotPath, uploadPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import type { Age } from "@/shared/time/age-groups"
import { isRecentDay } from "@/shared/time/age-groups"
import { Icon } from "@/shared/ui/icon"
import { MetaChip, MetaChips } from "@/shared/ui/meta-chip"
import { ProgressBar } from "@/shared/ui/progress-bar"
import styles from "./styles.module.css"

export const FILE_KINDS = ["csv", "xlsx", "pdf", "docx", "other"] as const
export type FileKind = (typeof FILE_KINDS)[number]

const EXTENSIONS: Readonly<Record<string, FileKind>> = {
  csv: "csv",
  txt: "csv",
  xlsx: "xlsx",
  xls: "xlsx",
  pdf: "pdf",
  docx: "docx",
  doc: "docx",
}

export function kindOf(fileName: string): FileKind {
  const extension = fileName.split(".").at(-1)?.toLowerCase() ?? ""
  return EXTENSIONS[extension] ?? "other"
}

type Fact = "lots" | "ready" | "attention"

function Facts({ upload, query }: { readonly upload: UploadSummary; readonly query: boolean }) {
  const { t } = useTranslation("history")
  const fact = (key: Fact, count: number) => (
    <Trans t={t} i18nKey={`row.${key}`} count={count} components={{ b: <b /> }} />
  )
  if (isProcessing(upload)) {
    return (
      <ProgressBar
        label={t("row.working")}
        value={upload.processed}
        max={upload.total}
        valueText={t("row.progress", { processed: upload.processed, total: upload.total })}
      />
    )
  }
  if (query) {
    return (
      <MetaChips>
        {upload.counts.ready > 0 ? (
          <MetaChip tone="accent">{t("row.found")}</MetaChip>
        ) : (
          <MetaChip tone="muted">{t("row.notFound")}</MetaChip>
        )}
      </MetaChips>
    )
  }
  const attention = upload.counts.noCandidates + upload.counts.failed
  return (
    <MetaChips>
      <MetaChip>{fact("lots", upload.total)}</MetaChip>
      {upload.counts.ready > 0 ? (
        <MetaChip>{fact("ready", upload.counts.ready)}</MetaChip>
      ) : null}
      {attention > 0 ? (
        <MetaChip tone="warning">{fact("attention", attention)}</MetaChip>
      ) : null}
    </MetaChips>
  )
}

export type HistoryRowProps = {
  readonly upload: UploadSummary
  readonly age: Age
  readonly query: boolean
}

export function HistoryRow({ upload, age, query }: HistoryRowProps) {
  const { t } = useTranslation("history")
  const { dateTime, time } = useFormatters()
  const kind = kindOf(upload.fileName)
  const to = query ? lotPath(upload.id, TEXT_QUERY_LOT) : uploadPath(upload.id)
  return (
    <Link to={to} className={styles.row} data-kind={query ? "query" : "file"}>
      {query ? null : (
        <span className={styles.kind} data-kind={kind}>
          {t(`kind.${kind}`)}
        </span>
      )}
      <span className={styles.body}>
        <span className={styles.title}>
          {query ? upload.title || upload.fileName : upload.fileName}
        </span>
        <span className={styles.meta}>
          <Facts upload={upload} query={query} />
          <time dateTime={upload.createdAt}>
            {isRecentDay(age) ? time(upload.createdAt) : dateTime(upload.createdAt)}
          </time>
        </span>
      </span>
      <span className={styles.chevron} aria-hidden="true">
        <Icon name="chevron" size="sm" />
      </span>
    </Link>
  )
}
