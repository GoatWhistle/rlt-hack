import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { MeterBasis } from "@/entities/evidence/model"
import styles from "./styles.module.css"

const BASIS_STYLES: Record<MeterBasis, string | undefined> = {
  stock: styles.stock,
  catalog: styles.catalog,
  historical: styles.catalog,
  inferred: styles.inferred,
  none: undefined,
}

export type MeterSegment = {
  readonly key: string
  readonly basis: MeterBasis
}

export type SegmentMeterProps = {
  readonly segments: readonly MeterSegment[]
  readonly size?: "sm" | "lg"
  readonly reveal?: boolean
}

export function SegmentMeter({ segments, size = "sm", reveal = false }: SegmentMeterProps) {
  const { t } = useTranslation("evidence")
  const count = (basis: MeterBasis) => segments.filter((item) => item.basis === basis).length
  const label = t("meter.label", {
    matched: segments.length - count("none"),
    total: segments.length,
    stock: count("stock"),
    catalog: count("catalog"),
    inferred: count("inferred"),
  })
  return (
    <span
      role="img"
      aria-label={
        count("historical") > 0
          ? `${label}; ${t("meter.history", { count: count("historical") })}`
          : label
      }
      className={clsx(styles.meter, size === "lg" && styles.large)}
      data-reveal={reveal ? "" : undefined}
    >
      {segments.map((segment) => (
        <span key={segment.key} className={clsx(styles.segment, BASIS_STYLES[segment.basis])} />
      ))}
    </span>
  )
}
