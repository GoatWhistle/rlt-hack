import { clsx } from "clsx"
import { type ReactNode, useState } from "react"
import { useTranslation } from "react-i18next"
import { Dot, type DotProps } from "@/shared/ui/dot"
import { RESULT_STATUSES, type ResultStatus } from "../model"
import { firstReveal } from "./reveal"
import styles from "./styles.module.css"

const SEGMENTS: Record<ResultStatus, string | undefined> = {
  ready: styles.ready,
  needsCheck: styles.needsCheck,
  noCandidates: styles.noCandidates,
  failed: styles.failed,
}

const MARKS: Record<ResultStatus, DotProps> = {
  ready: { shape: "filled", tone: "accent", size: "md" },
  needsCheck: { shape: "dashed", tone: "warning", size: "md" },
  noCandidates: { shape: "dashed", tone: "muted", size: "md" },
  failed: { shape: "hollow", tone: "danger", size: "md" },
}

export type StatusStripProps = {
  readonly counts: Readonly<Record<ResultStatus, number>>
  readonly total: number
  readonly lead?: ReactNode
  readonly trail?: ReactNode
  readonly compact?: boolean
  readonly live?: boolean
  readonly revealId?: string
}

export function StatusStrip({
  counts,
  total,
  lead,
  trail,
  compact = false,
  live = false,
  revealId,
}: StatusStripProps) {
  const { t } = useTranslation("uploads")
  const [reveal] = useState(() =>
    revealId
      ? firstReveal(`${revealId}:${total}:${RESULT_STATUSES.map((s) => counts[s]).join(",")}`)
      : false,
  )
  const shown = RESULT_STATUSES.filter((status) => counts[status] > 0)
  const done = shown.reduce((sum, status) => sum + counts[status], 0)
  const queued = Math.max(0, total - done)
  return (
    <div className={styles.strip}>
      <span className={styles.bar} aria-hidden="true" data-reveal={reveal || undefined}>
        {shown.map((status) => (
          <span
            key={status}
            className={clsx(styles.segment, SEGMENTS[status])}
            style={{ flexGrow: counts[status] }}
          />
        ))}
        {queued > 0 ? (
          <span
            className={clsx(styles.segment, styles.queued)}
            data-live={live || undefined}
            style={{ flexGrow: queued }}
          />
        ) : null}
      </span>
      {lead || shown.length > 0 || trail ? (
        <ul className={clsx(styles.legend, compact && styles.compact)}>
          {lead ? <li className={styles.item}>{lead}</li> : null}
          {shown.map((status) => (
            <li key={status} className={clsx(styles.item, styles.status)}>
              <Dot {...MARKS[status]} />
              {t(`list.${status}`, { count: counts[status] })}
            </li>
          ))}
          {trail ? <li className={styles.item}>{trail}</li> : null}
        </ul>
      ) : null}
    </div>
  )
}
