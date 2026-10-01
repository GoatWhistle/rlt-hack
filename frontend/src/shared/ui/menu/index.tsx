import type { KeyboardEvent, ReactNode, RefObject } from "react"
import { useEffect, useRef } from "react"
import { usePresence } from "@/shared/motion/use-presence"
import { Icon } from "@/shared/ui/icon"
import styles from "./styles.module.css"
import { useCheckedIndicator } from "./use-checked-indicator"

const ITEM = '[role^="menuitem"]'

function items(menu: HTMLElement | null): HTMLElement[] {
  return menu ? [...menu.querySelectorAll<HTMLElement>(ITEM)] : []
}

export function nextIndex(key: string, current: number, count: number): number | null {
  if (key === "ArrowDown") return (current + 1) % count
  if (key === "ArrowUp") return (current - 1 + count) % count
  if (key === "Home") return 0
  if (key === "End") return count - 1
  return null
}

export type MenuProps = {
  readonly id: string
  readonly open: boolean
  readonly label: string
  readonly triggerRef: RefObject<HTMLElement | null>
  readonly onClose: (restoreFocus: boolean) => void
  readonly children: ReactNode
}

export function Menu({ id, open, label, triggerRef, onClose, children }: MenuProps) {
  const ref = useRef<HTMLDivElement>(null)
  const { isMounted, state, onAnimationEnd } = usePresence(open)
  useCheckedIndicator(ref, isMounted)

  useEffect(() => {
    if (!open) return
    const all = items(ref.current)
    const checked = all.find((item) => item.getAttribute("aria-checked") === "true")
    ;(checked ?? all[0])?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const closeOutside = (event: PointerEvent) => {
      const target = event.target as Node
      if (ref.current?.contains(target) || triggerRef.current?.contains(target)) return
      onClose(false)
    }
    document.addEventListener("pointerdown", closeOutside)
    return () => document.removeEventListener("pointerdown", closeOutside)
  }, [open, onClose, triggerRef])

  if (!isMounted) return null

  const navigate = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault()
      onClose(true)
      return
    }
    if (event.key === "Tab") {
      onClose(false)
      return
    }
    const all = items(ref.current)
    const next = nextIndex(
      event.key,
      all.indexOf(document.activeElement as HTMLElement),
      all.length,
    )
    if (next === null) return
    event.preventDefault()
    all[next]?.focus()
  }

  return (
    <div
      ref={ref}
      id={id}
      role="menu"
      aria-label={label}
      data-state={state}
      className={styles.menu}
      onKeyDown={navigate}
      onAnimationEnd={onAnimationEnd}
    >
      <span className={styles.indicator} aria-hidden="true" />
      {children}
    </div>
  )
}

export type MenuItemRadioProps = {
  readonly checked: boolean
  readonly onSelect: () => void
  readonly children: ReactNode
}

export function MenuItemRadio({ checked, onSelect, children }: MenuItemRadioProps) {
  return (
    <button
      type="button"
      role="menuitemradio"
      aria-checked={checked}
      tabIndex={-1}
      className={styles.item}
      onClick={onSelect}
    >
      {children}
      <span className={styles.check}>{checked ? <Icon name="check" /> : null}</span>
    </button>
  )
}
