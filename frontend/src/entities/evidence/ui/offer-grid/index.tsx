import { clsx } from "clsx"
import { useId, useState } from "react"
import { useTranslation } from "react-i18next"
import type { OfferView } from "@/entities/evidence/model"
import { Bone } from "@/shared/ui/skeleton"
import { TextButton } from "@/shared/ui/text-button"
import { OfferCard, type OfferLink } from "../offer-card"
import styles from "./styles.module.css"

export type OfferEntry = {
  readonly key?: string
  readonly offer: OfferView
  readonly link?: OfferLink
}

export type OfferGridProps = {
  readonly entries: readonly OfferEntry[]
  readonly label: string
  readonly limit?: number
  readonly ribbon?: boolean
}

export function OfferGrid({ entries, label, limit, ribbon = false }: OfferGridProps) {
  const { t } = useTranslation()
  const id = useId()
  const [expanded, setExpanded] = useState(false)
  const hidden = limit === undefined ? 0 : entries.length - limit
  const visible = expanded || hidden <= 0 ? entries : entries.slice(0, limit)
  return (
    <div className={styles.wrap}>
      <ul id={id} aria-label={label} className={clsx(styles.grid, ribbon && styles.ribbon)}>
        {visible.map((entry, index) => (
          <li
            key={entry.key ?? entry.offer.id}
            className={clsx(styles.item, limit !== undefined && index >= limit && styles.added)}
          >
            <OfferCard offer={entry.offer} link={entry.link} />
          </li>
        ))}
      </ul>
      {hidden > 0 ? (
        <TextButton
          className={styles.more}
          aria-expanded={expanded}
          aria-controls={id}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? t("action.showLess") : t("action.showAll", { count: entries.length })}
        </TextButton>
      ) : null}
    </div>
  )
}

export type OfferGridSkeletonProps = {
  readonly count?: number
  readonly ribbon?: boolean
}

export function OfferGridSkeleton({ count = 2, ribbon = false }: OfferGridSkeletonProps) {
  const cards = Array.from({ length: count }, (_, index) => `offer-${index}`)
  return (
    <div className={clsx(styles.grid, ribbon && styles.ribbon)}>
      {cards.map((card) => (
        <div key={card} className={clsx(styles.item, styles.ghost)}>
          <Bone className={styles.title} />
          <Bone className={styles.meta} />
          <Bone className={styles.price} />
          <Bone className={styles.source} />
        </div>
      ))}
    </div>
  )
}

export type OfferEmptyProps = {
  readonly title: string
  readonly hint?: string
}

export function OfferEmpty({ title, hint }: OfferEmptyProps) {
  return (
    <div className={styles.empty}>
      <p className={styles.emptyTitle}>{title}</p>
      {hint ? <p className={styles.emptyHint}>{hint}</p> : null}
    </div>
  )
}
