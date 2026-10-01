import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Product, ProductOrigin } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { ResultSection } from "@/shared/ui/result-section"
import { Tag } from "@/shared/ui/tag"
import styles from "./styles.module.css"

export function OriginLabel({ origin }: { readonly origin: ProductOrigin }) {
  const { t } = useTranslation("lot")
  const label = t(`products.origin.${origin}`)
  if (origin === "inferred") {
    return (
      <Tag tone="warning">
        <Icon name="warning" size="sm" />
        {label}
      </Tag>
    )
  }
  if (origin === "user") {
    return (
      <Tag tone="accent">
        <Icon name="pencil" size="sm" />
        {label}
      </Tag>
    )
  }
  return (
    <span className={styles.notice}>
      <Icon name="check" tone="confirmed" size="sm" />
      {label}
    </span>
  )
}

type ProductRowProps = {
  readonly product: Product
  readonly active: boolean
  readonly onFilter: () => void
}

function useOriginNote(): (product: Product) => string {
  const { t } = useTranslation("lot")
  return ({ origin, originNote }) => {
    if (!originNote) return t(`products.originNote.${origin}`)
    if (originNote.code === "userSpecified") return t("products.note.userSpecified")
    return t("products.note.similarPurchases", {
      hits: originNote.hits,
      total: originNote.total,
    })
  }
}

function ProductRow({ product, active, onFilter }: ProductRowProps) {
  const { t } = useTranslation("lot")
  const noteOf = useOriginNote()
  return (
    <li className={clsx(styles.item, active && styles.active)}>
      <details className={styles.details}>
        <summary className={styles.summary}>
          <span className={styles.chevron}>
            <Icon name="chevron" size="sm" />
          </span>
          <span className={styles.body}>
            <span className={styles.name}>{product.name}</span>
            <OriginLabel origin={product.origin} />
          </span>
        </summary>
        <div className={styles.note}>
          <span className={styles.code}>{t("products.okpd2", { code: product.okpd2 })}</span>
          <p>{noteOf(product)}</p>
        </div>
      </details>
      <span className={styles.tool}>
        <button
          type="button"
          className={styles.filter}
          aria-pressed={active}
          aria-label={t("products.filter", { name: product.name })}
          onClick={onFilter}
        >
          <Icon name="filter" size="sm" />
        </button>
        <span className={styles.tip} aria-hidden="true">
          {active ? t("products.filterReset") : t("products.filterHint")}
        </span>
      </span>
    </li>
  )
}

export type ProductListProps = {
  readonly products: readonly Product[]
  readonly filterId: string | null
  readonly onFilter: (productId: string | null) => void
}

export function ProductList({ products, filterId, onFilter }: ProductListProps) {
  const { t } = useTranslation("lot")
  return (
    <ResultSection
      framed
      title={t("products.title")}
      aside={t("products.count", { count: products.length })}
    >
      <ul className={styles.list}>
        {products.map((product) => (
          <ProductRow
            key={product.id}
            product={product}
            active={product.id === filterId}
            onFilter={() => onFilter(product.id === filterId ? null : product.id)}
          />
        ))}
      </ul>
    </ResultSection>
  )
}
