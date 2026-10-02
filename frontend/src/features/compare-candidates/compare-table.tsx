import type { ReactNode } from "react"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { Icon } from "@/shared/ui/icon"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type CompareColumn = {
  readonly id: string
  readonly name: string
  readonly role: string
}

export type CompareCriterion<T> = {
  readonly id: string
  readonly label: string
  readonly value: (item: T) => ReactNode
  readonly score?: (item: T) => number
}

export function bestOf<T extends { readonly id: string }>(
  items: readonly T[],
  score: ((item: T) => number) | undefined,
): string | undefined {
  if (!score || items.length < 2) return undefined
  const ranked = items.map((item) => ({ id: item.id, value: score(item) }))
  const top = Math.max(...ranked.map((item) => item.value))
  const leaders = ranked.filter((item) => item.value === top)
  return leaders.length === 1 && top > 0 ? leaders[0]?.id : undefined
}

export function MissingNames({ names }: { readonly names: string }) {
  return (
    <span className={styles.missing}>
      <span className={styles.marker} aria-hidden="true" />
      {names}
    </span>
  )
}

export function MatchValue({
  figure,
  note,
  meter,
}: {
  readonly figure: string
  readonly note?: string
  readonly meter: ReactNode
}) {
  return (
    <span className={styles.match}>
      <span>
        {figure}
        {note ? <span className={styles.note}> {note}</span> : null}
      </span>
      {meter}
    </span>
  )
}

export type CompareTableProps<T extends CompareColumn> = {
  readonly open: boolean
  readonly title: string
  readonly criterionLabel: string
  readonly bestLabel: string
  readonly note: string
  readonly columns: readonly T[]
  readonly criteria: readonly CompareCriterion<T>[]
  readonly onClose: () => void
}

export function CompareTable<T extends CompareColumn>({
  open,
  title,
  criterionLabel,
  bestLabel,
  note,
  columns,
  criteria,
  onClose,
}: CompareTableProps<T>) {
  return (
    <Dialog open={open} size="wide" title={title} onClose={onClose}>
      <ScrollRegion label={title} className={styles.region}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col" className={styles.criterion}>
                {criterionLabel}
              </th>
              {columns.map((column) => (
                <th key={column.id} scope="col" className={styles.company}>
                  <span className={styles.companyName}>{column.name}</span>
                  <span className={styles.companyRole}>{column.role}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((criterion) => {
              const best = bestOf(columns, criterion.score)
              return (
                <tr key={criterion.id}>
                  <th scope="row" className={styles.criterion}>
                    {criterion.label}
                  </th>
                  {columns.map((column) => (
                    <td key={column.id} className={styles.cell}>
                      <span className={styles.value}>
                        <span className={styles.best}>
                          {column.id === best ? (
                            <>
                              <Icon name="check" size="sm" />
                              <VisuallyHidden>{bestLabel}</VisuallyHidden>
                            </>
                          ) : null}
                        </span>
                        <span className={column.id === best ? styles.leader : undefined}>
                          {criterion.value(column)}
                        </span>
                      </span>
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollRegion>
      <Caption>{note}</Caption>
    </Dialog>
  )
}
