import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Product, ProductOrigin } from "@/entities/recommendation/model"
import { EmptyState } from "@/shared/ui/empty-state"
import { Icon } from "@/shared/ui/icon"
import { Tag } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import styles from "./styles.module.css"

const BARS: Record<ProductOrigin, string | undefined> = {
  notice: undefined,
  inferred: styles.inferredBar,
  user: styles.userBar,
}

export function OriginLabel({ origin }: { readonly origin: ProductOrigin }) {
  const { t } = useTranslation("lot")
  const label = t(`products.origin.${origin}`)
  if (origin === "inferred") return <Tag tone="warning">{label}</Tag>
  if (origin === "user") return <Tag tone="accent">{label}</Tag>
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

function ProductRow({ product, active, onFilter }: ProductRowProps) {
  const { t } = useTranslation("lot")
  return (
    <li className={clsx(styles.item, active && styles.active)}>
      <details className={styles.details}>
        <summary className={styles.summary}>
          <span className={clsx(styles.bar, BARS[product.origin])} aria-hidden="true" />
          <span className={styles.body}>
            <span className={styles.name}>{product.name}</span>
            <span className={styles.meta}>
              <OriginLabel origin={product.origin} />
            </span>
          </span>
          <span className={styles.chevron}>
            <Icon name="chevron" size="sm" />
          </span>
        </summary>
        <div className={styles.note}>
          <span className={styles.code}>{t("products.okpd2", { code: product.okpd2 })}</span>
          <p>{product.originNote ?? t(`products.originNote.${product.origin}`)}</p>
        </div>
      </details>
      <button
        type="button"
        className={styles.filter}
        aria-pressed={active}
        aria-label={t("products.filter", { name: product.name })}
        onClick={onFilter}
      >
        <Icon name="filter" size="sm" />
      </button>
    </li>
  )
}

export type ProductListProps = {
  readonly products: readonly Product[]
  readonly requestTitle?: string
  readonly filterId: string | null
  readonly onFilter: (productId: string | null) => void
}

export function ProductList({ products, requestTitle, filterId, onFilter }: ProductListProps) {
  const { t } = useTranslation("lot")
  if (products.length === 0) {
    return (
      <EmptyState
        headingLevel={2}
        title={t("history.requestTitle")}
        description={t("history.requestNote", { title: requestTitle ?? "" })}
      />
    )
  }
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
