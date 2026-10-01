import { useTranslation } from "react-i18next"
import type { LotSummary, UploadSummary } from "@/entities/upload/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { BackLink } from "@/shared/ui/back-link"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { IconLink } from "@/shared/ui/icon-link"
import { SplitRow } from "@/shared/ui/split-row"
import { StepTrail } from "@/shared/ui/step-trail"
import styles from "./styles.module.css"

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
  const facts = [
    lot.customerInn ? t("header.customer", { inn: lot.customerInn }) : t("header.noCustomer"),
    lot.startPrice === undefined
      ? t("header.noPrice")
      : t("header.price", { price: money(lot.startPrice) }),
    ...(lot.publishDate ? [t("header.published", { date: date(lot.publishDate) })] : []),
  ]
  return (
    <header className={styles.header}>
      <div className={styles.top}>
        <BackLink to={backTo}>{t("header.back", { file: upload.fileName })}</BackLink>
        {neighbours ? (
          <nav className={styles.neighbours} aria-label={t("header.neighbours")}>
            {neighbours.prev ? (
              <IconLink to={neighbours.prev} icon="arrowLeft" label={t("header.prev")} />
            ) : null}
            <span className={styles.position}>
              {t("header.position", { index: neighbours.index, total: neighbours.total })}
            </span>
            {neighbours.next ? (
              <IconLink to={neighbours.next} icon="arrowRight" label={t("header.next")} />
            ) : null}
          </nav>
        ) : null}
      </div>
      <SplitRow>
        <div className={styles.titles}>
          <h1 className={styles.title}>{lot.title}</h1>
          <p className={styles.meta}>
            <span className={styles.code}>{t("header.lot", { id: lot.id })}</span>
            {facts.map((fact) => (
              <span key={fact}>{fact}</span>
            ))}
          </p>
        </div>
        <Button variant="secondary" onClick={onExport}>
          <Icon name="download" />
          {t("header.export")}
        </Button>
      </SplitRow>
      <StepTrail
        label={t("chain.label")}
        steps={[
          t("chain.request"),
          ...(lot.products > 0 ? [t("chain.products")] : []),
          t("chain.companies"),
          t("chain.evidence"),
        ]}
        current={lot.products > 0 ? 3 : 2}
      />
    </header>
  )
}
