import { useTranslation } from "react-i18next"
import type { RoleContext } from "@/entities/evidence/model"
import styles from "./styles.module.css"

export function RoleBasisNote({ context }: { readonly context: RoleContext }) {
  const { t } = useTranslation("evidence")
  const basis =
    context.basis === "offer" && context.product
      ? t("roleBasis.offerProduct", { product: context.product })
      : t(`roleBasis.${context.basis}`)
  return (
    <span className={styles.note}>
      <span>{basis}</span>
      {context.basis !== "offer" && context.note ? (
        <span className={styles.detail}>{context.note}</span>
      ) : null}
      {context.conflict ? (
        <span className={styles.conflict} role="note">
          {t("roleBasis.conflict", { note: context.note ?? "" })}
        </span>
      ) : null}
    </span>
  )
}
