import { useId } from "react"
import { useTranslation } from "react-i18next"
import { REGION_CODES } from "@/entities/evidence/regions"
import styles from "./styles.module.css"

type Props = {
  readonly value: string
  readonly onChange: (value: string) => void
  readonly disabled: boolean
}

export function RegionPreference({ value, onChange, disabled }: Props) {
  const { t } = useTranslation(["search", "evidence"])
  const id = useId()
  return (
    <div className={styles.preference}>
      <label htmlFor={id}>{t("search:box.region")}</label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={styles.select}
        aria-describedby={`${id}-hint`}
      >
        <option value="">{t("search:box.anyRegion")}</option>
        {REGION_CODES.map((code) => (
          <option key={code} value={code}>
            {t(`evidence:regionName.${code}`)}
          </option>
        ))}
      </select>
      <span id={`${id}-hint`} className={styles.hint}>
        {t("search:box.regionHint")}
      </span>
    </div>
  )
}
