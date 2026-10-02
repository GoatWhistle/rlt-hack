import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { type Candidate, matchOf, type QueryItem } from "@/entities/search/model"
import { Icon } from "@/shared/ui/icon"
import { ResultSection } from "@/shared/ui/result-section"
import { Tag } from "@/shared/ui/tag"
import { useQuantityText } from "../labels"
import styles from "./styles.module.css"

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

export type ItemListProps = {
  readonly items: readonly QueryItem[]
  readonly candidates: readonly Candidate[]
  readonly activeId: string | null
  readonly onFilter: (itemId: string | null) => void
}

export function ItemList({ items, candidates, activeId, onFilter }: ItemListProps) {
  const { t } = useTranslation("search")
  const quantityOf = useQuantityText()
  return (
    <ResultSection
      framed
      title={t("items.title")}
      aside={t("items.count", { count: items.length })}
    >
      <p className={styles.hint}>{t("items.hint")}</p>
      <ul className={styles.list}>
        {items.map((item) => {
          const active = item.id === activeId
          const covered = candidates.filter((candidate) => matchOf(candidate, item.id)).length
          const quantity = quantityOf(item)
          return (
            <li key={item.id} className={styles.entry}>
              <button
                type="button"
                className={clsx(styles.item, active && styles.active)}
                aria-pressed={active}
                onClick={() => onFilter(active ? null : item.id)}
              >
                <span className={styles.head}>
                  <span className={styles.name}>{item.name}</span>
                  <span className={styles.mark} aria-hidden="true">
                    <Icon name="filter" size="sm" />
                  </span>
                </span>
                <span className={styles.facts}>
                  {quantity ? <span className={styles.quantity}>{quantity}</span> : null}
                  {item.okpd2 ? (
                    <span className={styles.code}>
                      {t("items.okpd2", { code: item.okpd2 })}
                    </span>
                  ) : null}
                  <span className={styles.covered}>
                    {t("items.covered", { count: covered })}
                  </span>
                </span>
                <OriginTag item={item} />
              </button>
            </li>
          )
        })}
      </ul>
    </ResultSection>
  )
}
