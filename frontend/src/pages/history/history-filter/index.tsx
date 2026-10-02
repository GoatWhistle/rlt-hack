import { useId } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"

export type HistoryFilterProps = {
  readonly value: string
  readonly onChange: (value: string) => void
}

export function HistoryFilter({ value, onChange }: HistoryFilterProps) {
  const { t } = useTranslation("history")
  const id = useId()
  return (
    <div className={styles.filter}>
      <label htmlFor={id} className={styles.label}>
        {t("filter.label")}
      </label>
      <span className={styles.field}>
        <Icon name="search" />
        <input
          id={id}
          type="search"
          className={styles.input}
          value={value}
          placeholder={t("filter.placeholder")}
          autoComplete="off"
          onChange={(event) => onChange(event.target.value)}
        />
      </span>
    </div>
  )
}
