import { useTranslation } from "react-i18next"
import type { Company, MatchBasis, Product, Source } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Tag, type TagTone } from "@/shared/ui/tag"
import { Block } from "../block"
import { CollapsibleList } from "../collapsible-list"
import { FactRow } from "../fact-row"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

export const MATCH_LIMIT = 4

const BASIS_ORDER: Record<MatchBasis, number> = { stock: 0, catalog: 1, inferred: 2 }
const BASIS_TONE: Record<MatchBasis, TagTone> = {
  stock: "accent",
  catalog: "solid",
  inferred: "tentative",
}

type Row = {
  readonly product: Product
  readonly basis?: MatchBasis
  readonly source?: Source
}

function rows(company: Company, products: readonly Product[]): Row[] {
  const found = company.matches.flatMap((match) => {
    const product = products.find((item) => item.id === match.productId)
    return product ? [{ product, basis: match.basis, source: match.source }] : []
  })
  found.sort((a, b) => BASIS_ORDER[a.basis] - BASIS_ORDER[b.basis])
  const missing = products.filter((product) => !found.some((row) => row.product === product))
  return [...found, ...missing.map((product) => ({ product }))]
}

function MatchRow({ row }: { readonly row: Row }) {
  const { t } = useTranslation()
  return (
    <FactRow
      emphasis
      title={row.product.name}
      tag={
        <Tag tone={row.basis ? BASIS_TONE[row.basis] : "tentative"}>
          {row.basis
            ? t(`results.evidence.basis.${row.basis}`)
            : t("results.evidence.notFound")}
        </Tag>
      }
    >
      {row.basis ? <SourceLine source={row.source} /> : null}
    </FactRow>
  )
}

export type MatchBlockProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function MatchBlock({ company, products }: MatchBlockProps) {
  const { t } = useTranslation()
  return (
    <Block
      title={t("results.evidence.matchesTitle")}
      icon="link"
      tone="source"
      aside={
        <span className={styles.count}>
          {t("results.evidence.matchesCount", {
            matched: company.matches.length,
            total: products.length,
          })}
        </span>
      }
    >
      <Caption>{t("results.evidence.matchesHint")}</Caption>
      <CollapsibleList
        items={rows(company, products)}
        limit={MATCH_LIMIT}
        itemKey={(row) => row.product.id}
        renderItem={(row) => <MatchRow row={row} />}
      />
    </Block>
  )
}
