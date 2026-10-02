import {
  type KeyboardEvent,
  type RefObject,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { usePresence } from "@/shared/motion/use-presence"
import { Icon } from "@/shared/ui/icon"
import { ComboboxListbox } from "../listbox"
import type { ComboboxGroup, ComboboxItem, ComboboxText } from "../model"
import { nextActive, revealOption } from "../navigation"
import { sectionsFor } from "../search"
import { usePlacement } from "../use-placement"
import styles from "./styles.module.css"

export type ComboboxPanelProps = {
  readonly open: boolean
  readonly listId: string
  readonly value: string
  readonly groups: readonly ComboboxGroup[]
  readonly locale: string
  readonly text: ComboboxText
  readonly query: string
  readonly triggerRef: RefObject<HTMLElement | null>
  readonly onQuery: (query: string) => void
  readonly onClose: (restoreFocus: boolean) => void
  readonly onSelect: (value: string) => void
}

function useOutsidePress(
  open: boolean,
  panelRef: RefObject<HTMLElement | null>,
  triggerRef: RefObject<HTMLElement | null>,
  onClose: (restoreFocus: boolean) => void,
) {
  useEffect(() => {
    if (!open) return
    const press = (event: PointerEvent) => {
      const target = event.target as Node
      if (panelRef.current?.contains(target) || triggerRef.current?.contains(target)) return
      onClose(false)
    }
    document.addEventListener("pointerdown", press)
    return () => document.removeEventListener("pointerdown", press)
  }, [open, panelRef, triggerRef, onClose])
}

function pickActive(
  items: readonly ComboboxItem[],
  activeKey: string | null,
  value: string,
  searching: boolean,
): ComboboxItem | undefined {
  const chosen = items.find((item) => item.option.key === activeKey)
  if (chosen) return chosen
  if (searching) return items[0]
  return items.find((item) => item.option.value === value) ?? items[0]
}

export function ComboboxPanel(props: ComboboxPanelProps) {
  const { open, listId, value, query, locale, text, triggerRef, onClose, onSelect } = props
  const hintId = `${listId}-hint`
  const { isMounted, state, onAnimationEnd } = usePresence(open)
  const panelRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const revealActive = useRef(false)
  const [activeKey, setActiveKey] = useState<string | null>(null)
  const searching = query.trim() !== ""
  const sections = useMemo(
    () => sectionsFor(props.groups, query, locale),
    [props.groups, query, locale],
  )
  const items = useMemo(() => sections.flatMap((section) => section.items), [sections])
  const active = pickActive(items, activeKey, value, searching)
  const optionId = (key: string) => `${listId}-${key}`

  usePlacement(panelRef, triggerRef, open)
  useOutsidePress(open, panelRef, triggerRef, onClose)

  useEffect(() => {
    if (!open) return
    setActiveKey(null)
    const input = inputRef.current
    input?.focus({ preventScroll: true })
    input?.setSelectionRange(input.value.length, input.value.length)
  }, [open])

  useLayoutEffect(() => {
    const list = listRef.current
    if (!open || !list) return
    if (searching) list.scrollTop = 0
    else revealOption(list, list.querySelector<HTMLElement>('[aria-selected="true"]'), true)
  }, [open, searching])

  useLayoutEffect(() => {
    if (!revealActive.current || !active) return
    revealActive.current = false
    revealOption(listRef.current, document.getElementById(optionId(active.option.key)), false)
  })

  if (!isMounted) return null

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault()
      event.stopPropagation()
      onClose(true)
      return
    }
    if (event.key === "Tab") {
      onClose(false)
      return
    }
    if (event.key === "Enter") {
      event.preventDefault()
      if (active) onSelect(active.option.value)
      return
    }
    const next = nextActive(event.key, active ? items.indexOf(active) : -1, items.length)
    if (next === null) return
    event.preventDefault()
    revealActive.current = true
    setActiveKey(items[next]?.option.key ?? null)
  }

  return (
    <>
      <div className={styles.backdrop} data-state={state} aria-hidden="true" />
      <div
        ref={panelRef}
        className={styles.panel}
        data-state={state}
        inert={!open}
        onAnimationEnd={onAnimationEnd}
      >
        <div className={styles.header}>
          <span className={styles.title}>{text.label}</span>
          <button
            type="button"
            className={styles.close}
            aria-label={text.close}
            onClick={() => onClose(true)}
          >
            <Icon name="close" />
          </button>
        </div>
        <div className={styles.search}>
          <Icon name="search" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            className={styles.input}
            value={query}
            placeholder={text.search}
            aria-label={text.search}
            aria-describedby={text.hint ? hintId : undefined}
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active ? optionId(active.option.key) : undefined}
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            enterKeyHint="done"
            onChange={(event) => {
              props.onQuery(event.target.value)
              setActiveKey(null)
            }}
            onKeyDown={onKeyDown}
          />
        </div>
        <ComboboxListbox
          ref={listRef}
          id={listId}
          sections={sections}
          value={value}
          activeKey={active?.option.key ?? null}
          optionId={optionId}
          text={text}
          onActivate={setActiveKey}
          onSelect={onSelect}
        />
        {text.hint ? (
          <p id={hintId} className={styles.hint}>
            {text.hint}
          </p>
        ) : null}
      </div>
    </>
  )
}
