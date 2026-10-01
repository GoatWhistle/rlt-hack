import { useTranslation } from "react-i18next"
import { Caption } from "@/shared/ui/caption"
import { Block } from "../block"
import styles from "./styles.module.css"

export function ClarifyBlock({ items }: { readonly items: readonly string[] }) {
  const { t } = useTranslation()
  return (
    <Block title={t("results.evidence.clarifyTitle")} icon="warning" tone="current">
      {items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <Caption muted>{t("results.evidence.noClarify")}</Caption>
      )}
    </Block>
  )
}
