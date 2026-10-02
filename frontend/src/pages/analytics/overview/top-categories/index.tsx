import { useTranslation } from "react-i18next"
import type { AnalyticsFilters, Category } from "@/entities/analytics/model"
import { recordsHref, writeFilters } from "@/entities/analytics/scope"
import { analyticsCategoryPath } from "@/shared/config/paths"
import { PanelBlock } from "@/shared/ui/panel-block"
import { type Bar, BarList } from "../../bar-list"

export type TopCategoriesProps = {
  readonly categories: readonly Category[]
  readonly total: number
  readonly filters: AnalyticsFilters
}

export function TopCategories({ categories, total, filters }: TopCategoriesProps) {
  const { t } = useTranslation("analytics")
  const bars: Bar[] = categories.map((category) => ({
    key: category.code || "none",
    label: category.code
      ? `${category.code} ${category.name}`.trim()
      : t("categories.noCategory"),
    value: category.offers,
    href: category.code
      ? analyticsCategoryPath(category.code, writeFilters(filters))
      : recordsHref(filters, { problem: "no_category" }),
  }))
  return (
    <PanelBlock title={t("categories.top")}>
      <BarList bars={bars} total={total} />
    </PanelBlock>
  )
}
