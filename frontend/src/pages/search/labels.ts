import { useTranslation } from "react-i18next"
import type { QueryItem } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"

const NUMERIC = /^\d+(?:\.\d+)?$/

export function useQuantityText(): (item: QueryItem) => string | undefined {
  const { t } = useTranslation("search")
  const { number } = useFormatters()
  return ({ quantity }) => {
    if (!quantity) return undefined
    const value = NUMERIC.test(quantity.value) ? number(Number(quantity.value)) : quantity.value
    return quantity.unit ? t("items.quantity", { value, unit: quantity.unit }) : value
  }
}
