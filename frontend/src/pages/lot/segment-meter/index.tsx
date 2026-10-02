import type { MeterBasis } from "@/entities/evidence/model"
import { SegmentMeter as Meter } from "@/entities/evidence/ui/segment-meter"
import type { Company, Product } from "@/entities/recommendation/model"

export function basisOf(company: Company, product: Product): MeterBasis {
  return company.matches.find((match) => match.productId === product.id)?.basis ?? "none"
}

export type SegmentMeterProps = {
  readonly company: Company
  readonly products: readonly Product[]
  readonly size?: "sm" | "lg"
}

export function SegmentMeter({ company, products, size = "sm" }: SegmentMeterProps) {
  if (products.length === 0) return null
  return (
    <Meter
      size={size}
      segments={products.map((product) => ({
        key: product.id,
        basis: basisOf(company, product),
      }))}
    />
  )
}
