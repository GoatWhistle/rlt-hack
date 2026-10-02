import { useTranslation } from "react-i18next"
import type { Ratio } from "@/entities/analytics/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export function useRatioText(ratio: Ratio) {
  const { t } = useTranslation("analytics")
  const { percent } = useFormatters()
  const value = ratio.share === null ? t("ratio.noBase") : percent(ratio.share)
  const basis =
    ratio.denominator === 0
      ? t("ratio.noBase")
      : t("ratio.of", { numerator: ratio.numerator, denominator: ratio.denominator })
  const unknown = ratio.unknown > 0 ? t("ratio.unknown", { count: ratio.unknown }) : undefined
  return { value, basis, unknown, empty: ratio.share === null }
}

export type RatioCellProps = { readonly ratio: Ratio }

export function RatioCell({ ratio }: RatioCellProps) {
  const { value, basis, empty } = useRatioText(ratio)
  return (
    <span className={styles.cell} data-empty={empty || undefined}>
      <span aria-hidden={empty ? undefined : true}>{empty ? basis : value}</span>
      {empty ? null : <VisuallyHidden>{`${value}, ${basis}`}</VisuallyHidden>}
    </span>
  )
}
