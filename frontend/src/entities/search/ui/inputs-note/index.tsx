import { useTranslation } from "react-i18next"
import type { SearchResult } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import styles from "./styles.module.css"

const CONTEXT_FIELDS = ["customerInn", "startPrice"] as const

export function InputsNote({ result }: { readonly result: SearchResult }) {
  const { t } = useTranslation("search")
  const { list } = useFormatters()
  const given = CONTEXT_FIELDS.filter((field) => result.query.context[field])
  const user = result.items.some((item) => item.origin === "user")
  const used = result.pipeline.inputs.map((input) => t(`inputs.field.${input}`, input))
  const ignored = given.filter((field) => !result.pipeline.inputs.includes(field))
  return (
    <p className={styles.note}>
      {t("inputs.used", { fields: list(used) })}
      {user ? ` ${t("inputs.userItems")}` : ""}
      {ignored.length > 0
        ? ` ${t("inputs.ignored", { fields: list(ignored.map((field) => t(`inputs.field.${field}`))) })}`
        : ""}
    </p>
  )
}
