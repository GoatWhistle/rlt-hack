import { useCallback, useEffect, useId, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { LOCALES, type Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import { settleDelay } from "@/shared/motion/settle-delay"
import { Flag, type FlagCode } from "@/shared/ui/flag"
import { Icon } from "@/shared/ui/icon"
import { Menu, MenuItemRadio } from "@/shared/ui/menu"
import { ToolButton } from "@/shared/ui/tool-button"
import styles from "./styles.module.css"

const FLAGS: Record<Locale, FlagCode> = { ru: "ru", en: "gb" }

export function LocaleSwitch() {
  const { t } = useTranslation()
  const { locale, setLocale } = useLocale()
  const [open, setOpen] = useState(false)
  const menuId = useId()
  const trigger = useRef<HTMLButtonElement>(null)
  const settle = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(settle.current), [])

  const close = useCallback((restoreFocus: boolean) => {
    setOpen(false)
    if (restoreFocus) trigger.current?.focus()
  }, [])

  const choose = (next: Locale) => {
    setLocale(next)
    window.clearTimeout(settle.current)
    settle.current = window.setTimeout(() => close(true), settleDelay())
  }

  const label = t("language.current", { name: t(`language.${locale}`) })

  return (
    <div className={styles.switch}>
      <ToolButton
        ref={trigger}
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((current) => !current)}
      >
        <Icon name="globe" />
      </ToolButton>
      <Menu
        id={menuId}
        open={open}
        label={t("language.legend")}
        triggerRef={trigger}
        onClose={close}
      >
        {LOCALES.map((value) => (
          <MenuItemRadio key={value} checked={value === locale} onSelect={() => choose(value)}>
            <Flag code={FLAGS[value]} />
            <span lang={value}>{t(`language.${value}`)}</span>
          </MenuItemRadio>
        ))}
      </Menu>
    </div>
  )
}
