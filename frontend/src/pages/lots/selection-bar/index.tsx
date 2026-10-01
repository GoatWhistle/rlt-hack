import { useTranslation } from "react-i18next"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

export type SelectionBarProps = {
  readonly count: number
  readonly onExport: () => void
  readonly onClear: () => void
}

export function SelectionBar({ count, onExport, onClear }: SelectionBarProps) {
  const { t } = useTranslation("lots")
  return (
    <section className={styles.bar} aria-label={t("selection.label")}>
      <span className={styles.count}>{t("selection.count", { count })}</span>
      <span className={styles.actions}>
        <TextButton onClick={onClear}>{t("selection.clear")}</TextButton>
        <Button variant="strong" onClick={onExport}>
          <Icon name="download" />
          {t("selection.export")}
        </Button>
      </span>
    </section>
  )
}
