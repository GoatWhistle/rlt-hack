import { useTranslation } from "react-i18next"
import { useMatchFigure } from "@/entities/evidence/labels"
import { countMatches } from "@/entities/evidence/model"
import type { Company, MatchBasis, Product } from "@/entities/recommendation/model"
import {
  type CompareColumn,
  type CompareCriterion,
  CompareTable,
  MatchValue,
  MissingNames,
} from "@/features/compare-candidates"
import { useFormatters } from "@/shared/i18n/formatters"
import { SegmentMeter } from "../segment-meter"
import { useStatusText } from "../status"

export type CompareDialogProps = {
  readonly open: boolean
  readonly companies: readonly Company[]
  readonly products: readonly Product[]
  readonly onClose: () => void
}

type Column = CompareColumn & { readonly company: Company }

function useCriteria(products: readonly Product[]): CompareCriterion<Column>[] {
  const { t } = useTranslation("lot")
  const statusText = useStatusText()
  const figureOf = useMatchFigure()
  const { list, number } = useFormatters()
  const count = (company: Company, basis: MatchBasis) =>
    company.matches.filter((match) => match.basis === basis).length
  const known = (value: number | null) =>
    value === null ? t("compare.unknown") : number(value)
  const unmatched = (company: Company) => {
    const found = new Set(company.matches.map((match) => match.productId))
    const names = products.filter((product) => !found.has(product.id)).map((p) => p.name)
    return names.length > 0 ? <MissingNames names={list(names)} /> : t("compare.none")
  }
  const contacts = (company: Company) => {
    const { site, email, phone } = company.contacts ?? {}
    const given = [site, email, phone].filter(Boolean)
    return given.length > 0 ? given.join(" · ") : t("compare.unknown")
  }
  return [
    {
      id: "match",
      label: t("compare.match"),
      value: ({ company }) => {
        const figure = figureOf(company.matches, products.length)
        return (
          <MatchValue
            figure={figure.value}
            note={figure.note}
            meter={<SegmentMeter company={company} products={products} />}
          />
        )
      },
      score: ({ company }) => countMatches(company.matches).confirmed,
    },
    {
      id: "stock",
      label: t("evidence.basis.stock"),
      value: ({ company }) => number(count(company, "stock")),
      score: ({ company }) => count(company, "stock"),
    },
    {
      id: "catalog",
      label: t("evidence.basis.catalog"),
      value: ({ company }) => number(count(company, "catalog")),
    },
    {
      id: "inferred",
      label: t("evidence.basis.inferred"),
      value: ({ company }) => number(count(company, "inferred")),
    },
    { id: "missing", label: t("compare.missing"), value: ({ company }) => unmatched(company) },
    { id: "status", label: t("compare.status"), value: ({ company }) => statusText(company) },
    {
      id: "purchases",
      label: t("compare.purchases"),
      value: ({ company }) => known(company.similarPurchases),
      score: ({ company }) => company.similarPurchases ?? 0,
    },
    {
      id: "wins",
      label: t("compare.wins"),
      value: ({ company }) => known(company.wins),
      score: ({ company }) => company.wins ?? 0,
    },
    {
      id: "clarify",
      label: t("compare.clarify"),
      value: ({ company }) => company.clarify[0] ?? t("compare.none"),
    },
    { id: "contacts", label: t("compare.contacts"), value: ({ company }) => contacts(company) },
    {
      id: "inn",
      label: t("profile.inn"),
      value: ({ company }) => company.inn || t("compare.unknown"),
    },
  ]
}

export function CompareDialog({ open, companies, products, onClose }: CompareDialogProps) {
  const { t } = useTranslation("lot")
  const criteria = useCriteria(products)
  return (
    <CompareTable
      open={open}
      title={t("compare.title")}
      criterionLabel={t("compare.criterion")}
      bestLabel={t("compare.best")}
      note={t("compare.note")}
      columns={companies.map((company) => ({
        id: company.id,
        name: company.name,
        role: company.role,
        company,
      }))}
      criteria={criteria}
      onClose={onClose}
    />
  )
}
