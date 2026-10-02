import { type ReactNode, useState } from "react"
import { useTranslation } from "react-i18next"
import type { UploadSummary } from "@/entities/upload/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { groupByAge } from "@/shared/time/age-groups"
import { TextButton } from "@/shared/ui/text-button"
import { HistoryRow } from "../history-row"
import styles from "./styles.module.css"

export const HISTORY_STEP = 20

export type HistoryColumnProps = {
  readonly id: string
  readonly title: string
  readonly uploads: readonly UploadSummary[]
  readonly query: boolean
  readonly empty: ReactNode
  readonly hidden?: boolean
  readonly state?: ReactNode
}

export function HistoryColumn({
  id,
  title,
  uploads,
  query,
  empty,
  hidden,
  state,
}: HistoryColumnProps) {
  const { t } = useTranslation("history")
  const { number, relative } = useFormatters()
  const [shown, setShown] = useState(HISTORY_STEP)
  const visible = uploads.slice(0, shown)
  const rest = uploads.length - visible.length
  return (
    <section className={styles.column} aria-labelledby={id} hidden={hidden}>
      <header className={styles.head}>
        <h2 id={id} tabIndex={-1} className={styles.title}>
          {title}
        </h2>
        {state ? null : <span className={styles.count}>{number(uploads.length)}</span>}
      </header>
      {state ? (
        state
      ) : uploads.length === 0 ? (
        <div className={styles.empty}>{empty}</div>
      ) : (
        <div className={styles.scroll}>
          <ul className={styles.groups}>
            {groupByAge(visible).map((group) => (
              <li key={group.key}>
                <h3 className={styles.group}>{relative(group.age.value, group.age.unit)}</h3>
                <ul className={styles.list}>
                  {group.items.map((upload) => (
                    <li key={upload.id}>
                      <HistoryRow upload={upload} age={group.age} query={query} />
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
          {rest > 0 ? (
            <div className={styles.more}>
              <TextButton onClick={() => setShown((count) => count + HISTORY_STEP)}>
                {t("more", { count: Math.min(rest, HISTORY_STEP) })}
              </TextButton>
            </div>
          ) : null}
        </div>
      )}
    </section>
  )
}
