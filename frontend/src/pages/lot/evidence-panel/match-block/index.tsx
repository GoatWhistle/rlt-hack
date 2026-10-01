import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { Company, MatchBasis, Product, Source } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Icon } from "@/shared/ui/icon"
import { Stack } from "@/shared/ui/stack"
import { Fold } from "../fold"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

const BASIS_ORDER: Record<MatchBasis, number> = { stock: 0, catalog: 1, inferred: 2 }
const BASIS_STYLES: Record<MatchBasis, { marker?: string; label?: string }> = {
  stock: { marker: styles.stock, label: styles.stockLabel },
  catalog: { marker: styles.catalog },
  inferred: { marker: styles.inferred, label: styles.inferredLabel },
}

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

export function MatchRow({ row }: { readonly row: MatchRowData }) {
  const { t } = useTranslation("lot")
  const look = row.basis ? BASIS_STYLES[row.basis] : {}
  return (
    <div className={styles.row}>
      <span className={clsx(styles.marker, look.marker)} aria-hidden="true">
        {row.basis === "stock" ? <Icon name="check" size="sm" /> : null}
      </span>
      <div className={styles.body}>
        <div className={styles.head}>
          <span className={styles.product}>{row.product.name}</span>
          <span className={clsx(styles.basis, look.label)}>
            {row.basis ? t(`evidence.basis.${row.basis}`) : t("evidence.notFound")}
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
            <MatchRow row={row} />
          </li>
        ))}
      </Stack>
      <Caption>{t("evidence.matchesHint")}</Caption>
    </Fold>
  )
}
