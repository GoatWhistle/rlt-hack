import { useTranslation } from "react-i18next"
import type { HeaderColumn, PreviewRow } from "@/entities/notice/model"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import styles from "./styles.module.css"

export type PreviewTableProps = {
  readonly columns: readonly HeaderColumn[]
  readonly rows: readonly PreviewRow[]
}

export function PreviewTable({ columns, rows }: PreviewTableProps) {
  const { t } = useTranslation("uploads")
  return (
    <ScrollRegion label={t("dialog.previewRegion")}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col" className={styles.head}>
              {t("dialog.rowNumber")}
            </th>
            {columns.map((column) => (
              <th key={column.name} scope="col" className={styles.head}>
                {column.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.line}>
              <th scope="row" className={styles.line}>
                {row.line}
              </th>
              {columns.map((column, cellIndex) => (
                <td key={column.name} className={styles.cell}>
                  {row.cells[cellIndex]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </ScrollRegion>
  )
}
