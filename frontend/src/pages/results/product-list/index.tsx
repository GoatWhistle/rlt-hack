import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Product, ProductOrigin } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Icon, type IconName, type IconTone } from "@/shared/ui/icon"
import { ResultSection } from "../section"
import styles from "./styles.module.css"

type OriginLook = {
  readonly icon: IconName
  readonly tone: IconTone
  readonly className: string | undefined
}

const ORIGIN_LOOKS: Record<ProductOrigin, OriginLook> = {
  notice: { icon: "check", tone: "confirmed", className: styles.notice },
  inferred: { icon: "wave", tone: "current", className: styles.inferred },
  user: { icon: "pencil", tone: "source", className: styles.user },
}

export function OriginLabel({ origin }: { readonly origin: ProductOrigin }) {
  const { t } = useTranslation()
  const look = ORIGIN_LOOKS[origin]
  return (
    <span className={clsx(styles.origin, look.className)}>
      <Icon name={look.icon} tone={look.tone} size="sm" />
      {t(`results.products.origin.${origin}`)}
    </span>
  )
}

function ProductRow({ product }: { readonly product: Product }) {
  const { t } = useTranslation()
  return (
    <li className={styles.item}>
      <details className={styles.details}>
        <summary className={styles.summary}>
          <span className={styles.name}>{product.name}</span>
          <span className={styles.meta}>
            <OriginLabel origin={product.origin} />
            <Caption>{product.okpd2}</Caption>
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
    <ResultSection title={t("results.products.title")}>
      <ul className={styles.list}>
        {products.map((product) => (
          <ProductRow key={product.id} product={product} />
        ))}
      </ul>
    </ResultSection>
  )
}
