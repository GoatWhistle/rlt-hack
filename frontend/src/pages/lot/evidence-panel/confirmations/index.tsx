import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { Icon } from "@/shared/ui/icon"
import { PanelBlock as Block } from "@/shared/ui/panel-block"
import { Stack } from "@/shared/ui/stack"
import { MatchRow, matchRows } from "../match-block"
import styles from "./styles.module.css"

export const KEY_CONFIRMATIONS = 3

export type ConfirmationsProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function Confirmations({ company, products }: ConfirmationsProps) {
  const { t } = useTranslation("lot")
  const rows = matchRows(company, products)
  const confirmed = rows.filter((row) => row.basis && row.source).slice(0, KEY_CONFIRMATIONS)
  const missing = rows.filter((row) => !row.basis).map((row) => row.product.name)
  return (
    <Block title={t("evidence.confirmations")}>
      {confirmed.length > 0 ? (
        <Stack as="ul">
          {confirmed.map((row) => (
            <li key={row.product.id}>
              <MatchRow row={row} />
            </li>
          ))}
        </Stack>
      ) : (
        <p className={styles.warning}>
          <Icon name="warning" size="sm" tone="warning" />
          {t("evidence.noConfirmations")}
        </p>
      )}
      {missing.length > 0 ? (
        <p className={styles.warning}>
          <Icon name="warning" size="sm" tone="warning" />
          {t("evidence.unmatched", { count: missing.length, names: missing.join(", ") })}
        </p>
      ) : null}
    </Block>
  )
}
