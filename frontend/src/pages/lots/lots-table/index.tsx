import { clsx } from "clsx"
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

type LotRowProps = {
  readonly lot: LotSummary
  readonly href: string
  readonly selected: boolean
  readonly onToggle: () => void
}

function LotRow({ lot, href, selected, onToggle }: LotRowProps) {
  const { t } = useTranslation("lots")
  const { price, number } = useFormatters()
  const queued = lot.status === "queued"
  const amount = lot.startPrice === undefined ? undefined : price(lot.startPrice)
  const compact = [
    amount ?? t("table.priceMissing"),
    ...(queued
      ? []
      : [
          t("table.productCount", { count: lot.products }),
          t("table.candidateCount", { count: lot.candidates }),
        ]),
  ].join(" · ")
  return (
    <tr className={styles.row} data-selected={selected}>
      <td className={styles.check}>
        <label className={styles.boxArea}>
          <input
            type="checkbox"
            className={styles.box}
            aria-label={t("table.selectLot", { id: lot.id })}
            checked={selected}
            onChange={onToggle}
          />
        </label>
      </td>
      <td className={styles.lot}>
        <Link to={href} className={styles.link}>
          {lot.title}
        </Link>
        <span className={styles.meta}>
          {t("table.lot")} <span className={styles.code}>{lot.id}</span>
          {" · "}
          {lot.customerInn ? (
            <>
              {t("table.customer")} <span className={styles.code}>{lot.customerInn}</span>
            </>
          ) : (
            t("table.noCustomer")
          )}
        </span>
      </td>
      <td className={styles.status}>
        <LotStatusTag status={lot.status} />
      </td>
      <td className={clsx(styles.number, styles.wide)}>{amount ?? t("table.noPrice")}</td>
      <td className={clsx(styles.number, styles.wide)}>
        {queued ? t("table.pending") : number(lot.products)}
      </td>
      <td className={clsx(styles.number, styles.wide)}>
        {queued ? t("table.pending") : number(lot.candidates)}
      </td>
      <td className={styles.compact}>{compact}</td>
    </tr>
  )
}

export function LotsTable(props: LotsTableProps) {
  const { uploadId, fileName, lots, linkSearch, selected, onToggle, onTogglePage } = props
  const { t } = useTranslation("lots")
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
            <label className={styles.boxArea}>
              <input
                ref={all}
                type="checkbox"
                className={styles.box}
                aria-label={t("table.selectPage")}
                checked={pageIds.length > 0 && chosen === pageIds.length}
                onChange={(event) => onTogglePage(pageIds, event.target.checked)}
              />
            </label>
          </th>
          <th scope="col">{t("table.title")}</th>
          <th scope="col">{t("table.status")}</th>
          <th scope="col" className={styles.number}>
            {t("table.price")}
          </th>
          <th scope="col" className={styles.number}>
            {t("table.products")}
          </th>
          <th scope="col" className={styles.number}>
            {t("table.candidates")}
          </th>
        </tr>
      </thead>
      <tbody>
        {lots.map((lot) => (
          <LotRow
            key={lot.id}
            lot={lot}
            href={lotPath(uploadId, lot.id, linkSearch)}
            selected={selected.has(lot.id)}
            onToggle={() => onToggle(lot.id)}
          />
        ))}
      </tbody>
    </table>
  )
}
