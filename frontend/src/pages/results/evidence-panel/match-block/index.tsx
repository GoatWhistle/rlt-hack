import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, MatchBasis, Product, Source } from "@/entities/recommendation/model"
import { Block } from "../block"
import { CollapsibleList } from "../collapsible-list"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

export const MATCH_LIMIT = 4

const BASIS_ORDER: Record<MatchBasis, number> = { stock: 0, catalog: 1, inferred: 2 }
const BASIS_STYLES: Record<MatchBasis, { swatch?: string; label?: string }> = {
  stock: { swatch: styles.stock, label: styles.stockLabel },
  catalog: { swatch: styles.catalog },
  inferred: { swatch: styles.inferred, label: styles.inferredLabel },
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
  const look = row.basis ? BASIS_STYLES[row.basis] : {}
  return (
    <div className={styles.row}>
      <span className={clsx(styles.swatch, look.swatch)} aria-hidden="true" />
      <div className={styles.body}>
        <div className={styles.head}>
          <span className={styles.product}>{row.product.name}</span>
          <span className={clsx(styles.basis, look.label)}>
            {row.basis
              ? t(`results.evidence.basis.${row.basis}`)
              : t("results.evidence.notFound")}
          </span>
        </div>
        {row.basis ? <SourceLine source={row.source} /> : null}
      </div>
    </div>
  )
}

export type MatchBlockProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function MatchBlock({ company, products }: MatchBlockProps) {
  const { t } = useTranslation()
  return (
    <Block title={t("results.evidence.matchesTitle")} aside={t("results.evidence.matchesHint")}>
      <CollapsibleList
        items={rows(company, products)}
        limit={MATCH_LIMIT}
        itemKey={(row) => row.product.id}
        renderItem={(row) => <MatchRow row={row} />}
      />
    </Block>
  )
}
