import { useTranslation } from "react-i18next"
import type { LotSummary, UploadSummary } from "@/entities/upload/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { IconLink } from "@/shared/ui/icon-link"
import styles from "./styles.module.css"
import { NEXT_KEY, PREV_KEY, useNeighbourKeys } from "./use-neighbour-keys"

export type Neighbours = {
  readonly prev?: string
  readonly next?: string
  readonly index: number
  readonly total: number
}

export type LotHeaderProps = {
  readonly upload: UploadSummary
  readonly lot: LotSummary
  readonly backTo: string
  readonly neighbours?: Neighbours
  readonly onExport: () => void
}

export function LotHeader({ upload, lot, backTo, neighbours, onExport }: LotHeaderProps) {
  const { t } = useTranslation("lot")
  const { date, money } = useFormatters()
  useNeighbourKeys(neighbours?.prev, neighbours?.next)
  const facts = [
    lot.customerInn ? t("header.customer", { inn: lot.customerInn }) : t("header.noCustomer"),
    lot.startPrice === undefined
      ? t("header.noPrice")
      : t("header.price", { price: money(lot.startPrice) }),
    ...(lot.publishDate ? [t("header.published", { date: date(lot.publishDate) })] : []),
  ]
  return (
    <header className={styles.header}>
      <div className={styles.back}>
        <BackLink to={backTo}>{t("header.back", { file: upload.fileName })}</BackLink>
      </div>
      {neighbours ? (
        <nav className={styles.neighbours} aria-label={t("header.neighbours")}>
          <IconLink
            to={neighbours.prev}
            icon="arrowLeft"
            label={t("header.prev")}
            shortcut={PREV_KEY}
          />
          <span className={styles.position}>
            {t("header.position", { index: neighbours.index, total: neighbours.total })}
          </span>
          <IconLink
            to={neighbours.next}
            icon="arrowRight"
            label={t("header.next")}
            shortcut={NEXT_KEY}
          />
        </nav>
      ) : null}
      <h1 className={styles.title}>{lot.title}</h1>
      <p className={styles.meta}>
        <span className={styles.code}>{t("header.lot", { id: lot.id })}</span>
        {facts.map((fact) => (
          <span key={fact} className={styles.fact}>
            {fact}
          </span>
        ))}
      </p>
      <div className={styles.actions}>
        <Button variant="secondary" aria-label={t("header.export")} onClick={onExport}>
          <Icon name="download" />
          <span className={styles.full}>{t("header.export")}</span>
          <span className={styles.short}>{t("header.exportShort")}</span>
        </Button>
      </div>
    </header>
  )
}
