import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import { PanelBlock } from "@/shared/ui/panel-block"
import styles from "./styles.module.css"

export function ClarifyBlock({ items }: { readonly items: readonly string[] }) {
  const { t } = useTranslation("candidate")
  if (items.length === 0) return null
  return (
    <PanelBlock title={t("panel.clarifyTitle")}>
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item} className={styles.item}>
            <Icon name="warning" size="sm" tone="warning" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </PanelBlock>
  )
}
