import { useTranslation } from "react-i18next"
import type { Product, ProductOrigin } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Icon, type IconName, type IconTone } from "@/shared/ui/icon"
import { Tag, type TagTone } from "@/shared/ui/tag"
import { ResultSection } from "../section"
import styles from "./styles.module.css"

type OriginLook = { readonly tag: TagTone; readonly icon: IconName; readonly tone: IconTone }

const ORIGIN_LOOKS: Record<ProductOrigin, OriginLook> = {
  notice: { tag: "solid", icon: "check", tone: "confirmed" },
  inferred: { tag: "tentative", icon: "wave", tone: "current" },
  user: { tag: "accent", icon: "pencil", tone: "source" },
}

export function OriginTag({ origin }: { readonly origin: ProductOrigin }) {
  const { t } = useTranslation()
  const look = ORIGIN_LOOKS[origin]
  return (
    <Tag tone={look.tag}>
      <Icon name={look.icon} tone={look.tone} size="sm" />
      {t(`results.products.origin.${origin}`)}
    </Tag>
  )
}

export function ProductList({ products }: { readonly products: readonly Product[] }) {
  const { t } = useTranslation()
  return (
    <ResultSection title={t("results.products.title")} width="narrow">
      <ul className={styles.list}>
        {products.map((product) => (
          <li key={product.id} className={styles.item}>
            <span className={styles.name}>{product.name}</span>
            <span className={styles.meta}>
              <OriginTag origin={product.origin} />
              <Caption>{product.okpd2}</Caption>
            </span>
          </li>
        ))}
      </ul>
    </ResultSection>
  )
}
