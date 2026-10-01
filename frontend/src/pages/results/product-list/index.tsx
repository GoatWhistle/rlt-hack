import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Product, ProductOrigin } from "@/entities/recommendation/model"
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
  const { t } = useTranslation()
  const label = t(`results.products.origin.${origin}`)
  if (origin === "inferred") return <Tag tone="warning">{label}</Tag>
  if (origin === "user") return <Tag tone="accent">{label}</Tag>
  return (
    <span className={styles.notice}>
      <Icon name="check" tone="confirmed" size="sm" />
      {label}
    </span>
  )
}

function ProductRow({ product }: { readonly product: Product }) {
  const { t } = useTranslation()
  return (
    <li className={styles.item}>
      <details className={styles.details}>
        <summary className={styles.summary}>
          <span className={clsx(styles.bar, BARS[product.origin])} aria-hidden="true" />
          <span className={styles.body}>
            <span className={styles.name}>{product.name}</span>
            <span className={styles.meta}>
              <OriginLabel origin={product.origin} />
              <span className={styles.code}>{product.okpd2}</span>
            </span>
          </span>
          <span className={styles.chevron}>
            <Icon name="chevron" size="sm" />
          </span>
        </summary>
        <p className={styles.note}>
          {product.originNote ?? t(`results.products.originNote.${product.origin}`)}
        </p>
      </details>
    </li>
  )
}

export function ProductList({ products }: { readonly products: readonly Product[] }) {
  const { t } = useTranslation()
  return (
    <ResultSection
      framed
      title={t("results.products.title")}
      aside={t("results.products.count", { count: products.length })}
    >
      <ul className={styles.list}>
        {products.map((product) => (
          <ProductRow key={product.id} product={product} />
        ))}
      </ul>
    </ResultSection>
  )
}
