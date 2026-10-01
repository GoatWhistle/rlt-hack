import { useTranslation } from "react-i18next"
import { Caption } from "@/shared/ui/caption"
import { Fold } from "../fold"
import styles from "./styles.module.css"

export function ClarifyBlock({ items }: { readonly items: readonly string[] }) {
  const { t } = useTranslation("lot")
  return (
    <Fold
      title={t("evidence.clarifyTitle")}
      aside={t("evidence.clarifyAside", { count: items.length })}
    >
      {items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item}>
              <label className={styles.item}>
                <input type="checkbox" className={styles.box} />
                <span>{item}</span>
              </label>
            </li>
          ))}
        </ul>
      ) : (
        <Caption>{t("evidence.noClarify")}</Caption>
      )}
    </Fold>
  )
}
