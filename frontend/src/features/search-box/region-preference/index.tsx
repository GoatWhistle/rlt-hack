import { useTranslation } from "react-i18next"
import { isRegionCode } from "@/entities/evidence/regions"
import { LOCALE_TAGS } from "@/shared/i18n/locale"
import { Combobox } from "@/shared/ui/combobox"
import { useRegionGroups } from "./region-groups"

type Props = {
  readonly value: string
  readonly onChange: (value: string) => void
  readonly disabled: boolean
  readonly className?: string
  readonly collapse?: boolean
}

export function RegionPreference(props: Props) {
  const { value, onChange, disabled, className, collapse } = props
  const { t } = useTranslation(["search", "evidence"])
  const { locale, groups } = useRegionGroups()
  const name = isRegionCode(value)
    ? t(`evidence:regionName.${value}`)
    : t("search:box.anyRegion")
  return (
    <Combobox
      className={className}
      collapse={collapse}
      icon="pin"
      value={value}
      valueLabel={name}
      groups={groups}
      locale={LOCALE_TAGS[locale]}
      disabled={disabled}
      text={{
        label: t("search:box.region"),
        trigger: t("search:box.regionPicker.trigger", { name }),
        search: t("search:box.regionPicker.search"),
        empty: t("search:box.regionPicker.empty"),
        emptyHint: t("search:box.regionPicker.emptyHint"),
        close: t("search:box.regionPicker.close"),
      }}
      onChange={onChange}
    />
  )
}
