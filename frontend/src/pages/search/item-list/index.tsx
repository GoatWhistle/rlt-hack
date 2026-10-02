import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { countMatches } from "@/entities/evidence/model"
import { type Candidate, matchOf, type QueryItem } from "@/entities/search/model"
import { Fold } from "@/shared/ui/fold"
import { Icon } from "@/shared/ui/icon"
import { ResultSection } from "@/shared/ui/result-section"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import { Tag } from "@/shared/ui/tag"
import { useQuantityText } from "../labels"
import styles from "./styles.module.css"

export const ALL_ITEMS = "all"

function OriginTag({ item }: { readonly item: QueryItem }) {
  const { t } = useTranslation("search")
  if (item.origin === "text") return null
  const inferred = item.origin === "inferred"
  return (
    <Tag tone={inferred ? "warning" : "accent"}>
      <Icon name={inferred ? "warning" : "pencil"} size="sm" />
      {t(`items.origin.${item.origin}`)}
    </Tag>
  )
}

function Coverage({
  item,
  candidates,
}: {
  readonly item: QueryItem
  readonly candidates: readonly Candidate[]
}) {
  const { t: label } = useTranslation("candidate")
  const { t: evidence } = useTranslation("evidence")
  const found = candidates.flatMap((candidate) => matchOf(candidate, item.id) ?? [])
  const { confirmed, assumed } = countMatches(found)
  if (confirmed === 0 && assumed === 0) {
    return <span className={styles.covered}>{label("items.none")}</span>
  }
  return (
    <>
      {confirmed > 0 ? (
        <span className={styles.covered}>{label("items.covered", { count: confirmed })}</span>
      ) : null}
      {assumed > 0 ? (
        <span className={styles.assumed}>
          {confirmed > 0 ? " " : null}
          {evidence("assumed", { count: assumed })}
        </span>
      ) : null}
    </>
  )
}

export type ItemListProps = {
  readonly items: readonly QueryItem[]
  readonly candidates: readonly Candidate[]
  readonly activeId: string | null
  readonly compact?: boolean
  readonly onFilter?: (itemId: string | null) => void
}

function ItemRows({ items, candidates, activeId, onFilter }: ItemListProps) {
  const { t } = useTranslation("search")
  const quantityOf = useQuantityText()
  return (
    <ul className={styles.list}>
      {items.map((item) => {
        const active = item.id === activeId
        const quantity = quantityOf(item)
        const body = (
          <>
            <span className={styles.head}>
              <span className={styles.name}>{item.name}</span>
              {onFilter ? (
                <span className={styles.mark} aria-hidden="true">
                  <Icon name="filter" size="sm" />
                </span>
              ) : null}
            </span>
            <span className={styles.facts}>
              {quantity ? <span className={styles.quantity}>{quantity}</span> : null}
              {item.okpd2 ? (
                <span className={styles.code}>{t("items.okpd2", { code: item.okpd2 })}</span>
              ) : null}
              {onFilter ? <Coverage item={item} candidates={candidates} /> : null}
            </span>
            <OriginTag item={item} />
          </>
        )
        return (
          <li key={item.id} className={styles.entry}>
            {onFilter ? (
              <button
                type="button"
                className={clsx(styles.item, active && styles.active)}
                aria-pressed={active}
                onClick={() => onFilter(active ? null : item.id)}
              >
                {body}
              </button>
            ) : (
              <div className={styles.item}>{body}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function ItemList(props: ItemListProps) {
  const { t } = useTranslation("search")
  const { items, activeId, compact = false, onFilter } = props
  const title = t("items.title")
  const aside = t("items.count", { count: items.length })
  if (compact && onFilter) {
    return (
      <ResultSection title={title} aside={aside}>
        <SegmentedControl
          scroll
          legend={t("items.hint")}
          value={activeId ?? ALL_ITEMS}
          onChange={(value) => onFilter(value === ALL_ITEMS ? null : value)}
          options={[
            { value: ALL_ITEMS, label: t("items.all") },
            ...items.map((item) => ({ value: item.id, label: item.name })),
          ]}
        />
        <Fold title={t("items.details")}>
          <ItemRows {...props} />
        </Fold>
      </ResultSection>
    )
  }
  return (
    <ResultSection framed title={title} aside={aside}>
      {onFilter ? <p className={styles.hint}>{t("items.hint")}</p> : null}
      <ItemRows {...props} />
    </ResultSection>
  )
}
