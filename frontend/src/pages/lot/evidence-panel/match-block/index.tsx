import { useTranslation } from "react-i18next"
import type { MatchBasis, Source } from "@/entities/evidence/model"
import { BASIS_ORDER, MatchRow } from "@/entities/evidence/ui/match-row"
import type { Company, Product } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Fold } from "@/shared/ui/fold"
import { Stack } from "@/shared/ui/stack"

export type MatchRowData = {
  readonly product: Product
  readonly basis?: MatchBasis
  readonly source?: Source
}

export function matchRows(company: Company, products: readonly Product[]): MatchRowData[] {
  const found = company.matches.flatMap((match) => {
    const product = products.find((item) => item.id === match.productId)
    return product ? [{ product, basis: match.basis, source: match.source }] : []
  })
  found.sort((a, b) => BASIS_ORDER[a.basis] - BASIS_ORDER[b.basis])
  const missing = products.filter((product) => !found.some((row) => row.product === product))
  return [...found, ...missing.map((product) => ({ product }))]
}

export function ProductMatchRow({ row }: { readonly row: MatchRowData }) {
  return <MatchRow name={row.product.name} basis={row.basis} source={row.source} />
}

export type MatchBlockProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function MatchBlock({ company, products }: MatchBlockProps) {
  const { t } = useTranslation("lot")
  return (
    <Fold
      title={t("evidence.matchesTitle")}
      aside={t("evidence.matchesAside", {
        matched: company.matches.length,
        total: products.length,
      })}
    >
      <Stack as="ul">
        {matchRows(company, products).map((row) => (
          <li key={row.product.id}>
            <ProductMatchRow row={row} />
          </li>
        ))}
      </Stack>
      <Caption>{t("evidence.matchesHint")}</Caption>
    </Fold>
  )
}
