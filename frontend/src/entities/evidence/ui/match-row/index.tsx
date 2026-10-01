import { clsx } from "clsx"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import type { MatchBasis, Source } from "@/entities/evidence/model"
import { Icon } from "@/shared/ui/icon"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

export const BASIS_ORDER: Record<MatchBasis, number> = { stock: 0, catalog: 1, inferred: 2 }

const BASIS_STYLES: Record<MatchBasis, { marker?: string; label?: string }> = {
  stock: { marker: styles.stock, label: styles.stockLabel },
  catalog: { marker: styles.catalog },
  inferred: { marker: styles.inferred, label: styles.inferredLabel },
}

export function BasisMarker({ basis }: { readonly basis?: MatchBasis }) {
  const look = basis ? BASIS_STYLES[basis] : {}
  return (
    <span className={clsx(styles.marker, look.marker)} aria-hidden="true">
      {basis === "stock" ? <Icon name="check" size="sm" /> : null}
    </span>
  )
}

export type MatchRowProps = {
  readonly name: string
  readonly basis?: MatchBasis
  readonly source?: Source
  readonly note?: ReactNode
}

export function MatchRow({ name, basis, source, note }: MatchRowProps) {
  const { t } = useTranslation("evidence")
  const look = basis ? BASIS_STYLES[basis] : {}
  return (
    <div className={styles.row}>
      <BasisMarker basis={basis} />
      <div className={styles.body}>
        <div className={styles.head}>
          <span className={styles.product}>{name}</span>
          <span className={clsx(styles.basis, look.label)}>
            {basis ? t(`basis.${basis}`) : t("notFound")}
          </span>
        </div>
        {basis ? <SourceLine source={source} /> : null}
        {note}
      </div>
    </div>
  )
}
