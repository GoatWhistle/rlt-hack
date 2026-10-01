import { useTranslation } from "react-i18next"
import { LOCALES } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import { SegmentedControl } from "@/shared/ui/segmented-control"

export function LocaleSwitch() {
  const { t } = useTranslation()
  const { locale, setLocale } = useLocale()
  const options = LOCALES.map((value) => ({
    value,
    label: value.toUpperCase(),
    description: t(`language.${value}`),
  }))
  return (
    <SegmentedControl
      legend={t("language.legend")}
      options={options}
      value={locale}
      onChange={setLocale}
    />
  )
}
