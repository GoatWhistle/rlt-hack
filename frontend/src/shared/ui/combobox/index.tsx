import { clsx } from "clsx"
import { type KeyboardEvent, useCallback, useId, useRef, useState } from "react"
import { Icon, type IconName } from "@/shared/ui/icon"
import { Truncate } from "@/shared/ui/truncate"
import type { ComboboxGroup, ComboboxText } from "./model"
import { isTypeahead } from "./navigation"
import { ComboboxPanel } from "./panel"
import styles from "./styles.module.css"

export type { ComboboxGroup, ComboboxOption, ComboboxText } from "./model"

const OPEN_KEYS = new Set(["ArrowDown", "ArrowUp"])

export type ComboboxProps = {
  readonly id?: string
  readonly className?: string
  readonly collapse?: boolean
  readonly value: string
  readonly valueLabel: string
  readonly groups: readonly ComboboxGroup[]
  readonly locale: string
  readonly text: ComboboxText
  readonly icon?: IconName
  readonly disabled?: boolean
  readonly onChange: (value: string) => void
}

export function Combobox(props: ComboboxProps) {
  const { value, valueLabel, icon, text, disabled = false, onChange } = props
  const ownId = useId()
  const listId = `${ownId}-list`
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")

  const close = useCallback((restoreFocus: boolean) => {
    setOpen(false)
    if (restoreFocus) triggerRef.current?.focus()
  }, [])

  if (disabled && open) setOpen(false)

  const show = (seed: string) => {
    if (disabled) return
    setQuery(seed)
    setOpen(true)
  }

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (open) return
    if (OPEN_KEYS.has(event.key)) {
      event.preventDefault()
      show("")
    } else if (isTypeahead(event)) {
      event.preventDefault()
      show(event.key)
    }
  }

  return (
    <div
      className={clsx(styles.combobox, props.className)}
      data-collapse={props.collapse || undefined}
    >
      <button
        ref={triggerRef}
        id={props.id}
        type="button"
        className={styles.trigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-label={text.trigger}
        disabled={disabled}
        data-empty={value === "" || undefined}
        onClick={() => (open ? close(true) : show(""))}
        onKeyDown={onKeyDown}
      >
        {icon ? (
          <span className={styles.glyph}>
            <Icon name={icon} />
          </span>
        ) : null}
        <Truncate className={styles.value}>{valueLabel}</Truncate>
        <span className={styles.chevron}>
          <Icon name="chevron" />
        </span>
      </button>
      <ComboboxPanel
        open={open}
        listId={listId}
        value={value}
        groups={props.groups}
        locale={props.locale}
        text={text}
        query={query}
        triggerRef={triggerRef}
        onQuery={setQuery}
        onClose={close}
        onSelect={(next) => {
          onChange(next)
          close(true)
        }}
      />
    </div>
  )
}
