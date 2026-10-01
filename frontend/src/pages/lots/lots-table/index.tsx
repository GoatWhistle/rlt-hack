import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router"
import { LotStatusTag } from "@/entities/upload/lot-status"
import type { LotSummary } from "@/entities/upload/model"
import { lotPath } from "@/shared/config/paths"
import { useFormatters } from "@/shared/i18n/formatters"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type LotsTableProps = {
  readonly uploadId: string
  readonly fileName: string
  readonly lots: readonly LotSummary[]
  readonly linkSearch: string
  readonly selected: ReadonlySet<string>
  readonly onToggle: (lotId: string) => void
  readonly onTogglePage: (lotIds: readonly string[], checked: boolean) => void
}

export function LotsTable(props: LotsTableProps) {
  const { uploadId, fileName, lots, linkSearch, selected, onToggle, onTogglePage } = props
  const { t } = useTranslation("lots")
  const { money, number } = useFormatters()
  const pageIds = lots.map((lot) => lot.id)
  const chosen = pageIds.filter((id) => selected.has(id)).length
  const all = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (all.current) all.current.indeterminate = chosen > 0 && chosen < pageIds.length
  }, [chosen, pageIds.length])

  return (
    <table className={styles.table}>
      <caption>
        <VisuallyHidden>{t("table.caption", { name: fileName })}</VisuallyHidden>
      </caption>
      <thead className={styles.head}>
        <tr>
          <th scope="col" className={styles.check}>
            <input
              ref={all}
              type="checkbox"
              className={styles.box}
              aria-label={t("table.selectPage")}
              checked={pageIds.length > 0 && chosen === pageIds.length}
              onChange={(event) => onTogglePage(pageIds, event.target.checked)}
            />
          </th>
          <th scope="col">{t("table.title")}</th>
          <th scope="col" className={styles.number}>
            {t("table.price")}
          </th>
          <th scope="col" className={styles.number}>
            {t("table.products")}
          </th>
          <th scope="col" className={styles.number}>
            {t("table.candidates")}
          </th>
          <th scope="col">{t("table.status")}</th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => {
          const queued = lot.status === "queued"
          return (
            <tr key={lot.id} className={styles.row} data-selected={selected.has(lot.id)}>
              <td className={styles.check}>
                <input
                  type="checkbox"
                  className={styles.box}
                  aria-label={t("table.selectLot", { id: lot.id })}
                  checked={selected.has(lot.id)}
                  onChange={() => onToggle(lot.id)}
                />
              </td>
              <td className={styles.lot}>
                <Link to={lotPath(uploadId, lot.id, linkSearch)} className={styles.link}>
                  {lot.title}
                </Link>
                <span className={styles.meta}>
                  <span className={styles.code}>{t("table.lot", { id: lot.id })}</span>
                  {" · "}
                  {lot.customerInn
                    ? t("table.customer", { inn: lot.customerInn })
                    : t("table.noCustomer")}
                </span>
              </td>
              <td className={styles.number} data-label={t("table.price")}>
                {lot.startPrice === undefined ? t("table.noPrice") : money(lot.startPrice)}
              </td>
              <td className={styles.number} data-label={t("table.products")}>
                {queued ? t("table.pending") : number(lot.products)}
              </td>
              <td className={styles.number} data-label={t("table.candidates")}>
                {queued ? t("table.pending") : number(lot.candidates)}
              </td>
              <td className={styles.status}>
                <LotStatusTag status={lot.status} />
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
