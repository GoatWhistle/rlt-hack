import { useTranslation } from "react-i18next"
import type { Company, Product } from "@/entities/recommendation/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Dot } from "@/shared/ui/dot"
import { Icon } from "@/shared/ui/icon"
import { PanelBlock } from "@/shared/ui/panel-block"
import { Stack } from "@/shared/ui/stack"
import { matchRows, ProductMatchRow } from "../match-block"
import styles from "./styles.module.css"

export const KEY_CONFIRMATIONS = 3

export type ConfirmationsProps = {
  readonly company: Company
  readonly products: readonly Product[]
}

export function Confirmations({ company, products }: ConfirmationsProps) {
  const { t } = useTranslation("lot")
  const { list } = useFormatters()
  const rows = matchRows(company, products)
  const confirmed = rows.filter((row) => row.basis && row.source).slice(0, KEY_CONFIRMATIONS)
  const missing = rows.filter((row) => !row.basis).map((row) => row.product.name)
  return (
    <PanelBlock title={t("evidence.confirmations")}>
      {confirmed.length > 0 ? (
        <Stack as="ul">
          {confirmed.map((row) => (
            <li key={row.product.id}>
              <ProductMatchRow row={row} />
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
        <p className={styles.missing}>
          <Dot shape="dashed" tone="muted" size="md" />
          {t("evidence.unmatched", { count: missing.length, names: list(missing) })}
        </p>
      ) : null}
    </PanelBlock>
  )
}
