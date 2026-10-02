import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type DataColumn = {
  readonly key: string
  readonly label: string
  readonly numeric?: boolean
}

export type DataTableProps = {
  readonly label: string
  readonly columns: readonly DataColumn[]
  readonly children: ReactNode
}

export function DataTable({ label, columns, children }: DataTableProps) {
  return (
    <div className={styles.scroll}>
      <table className={styles.table} aria-label={label}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={clsx(column.numeric && styles.number)}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

export type DataCellProps = {
  readonly numeric?: boolean
  readonly children: ReactNode
}

export function DataCell({ numeric = false, children }: DataCellProps) {
  return <td className={clsx(numeric && styles.number)}>{children}</td>
}
