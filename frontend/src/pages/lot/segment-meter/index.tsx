import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, MatchBasis, Product } from "@/entities/recommendation/model"
import styles from "./styles.module.css"

export type MeterBasis = MatchBasis | "none"

const BASIS_STYLES: Record<MeterBasis, string | undefined> = {
  stock: styles.stock,
  catalog: styles.catalog,
  inferred: styles.inferred,
  none: undefined,
}

export function basisOf(company: Company, product: Product): MeterBasis {
  return company.matches.find((match) => match.productId === product.id)?.basis ?? "none"
}

export type SegmentMeterProps = {
  readonly company: Company
  readonly products: readonly Product[]
  readonly size?: "sm" | "lg"
}

export function SegmentMeter({ company, products, size = "sm" }: SegmentMeterProps) {
  const { t } = useTranslation("lot")
  const bases = products.map((product) => basisOf(company, product))
  const count = (basis: MeterBasis) => bases.filter((item) => item === basis).length
  const label = t("meter.label", {
    matched: bases.length - count("none"),
    total: bases.length,
    stock: count("stock"),
    catalog: count("catalog"),
    inferred: count("inferred"),
  })
  return (
    <span
      role="img"
      aria-label={label}
      className={clsx(styles.meter, size === "lg" && styles.large)}
    >
      {products.map((product, index) => (
        <span
          key={product.id}
          className={clsx(styles.segment, BASIS_STYLES[bases[index] ?? "none"])}
        />
      ))}
    </span>
  )
}
