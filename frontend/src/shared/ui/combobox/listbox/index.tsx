import { Fragment, type Ref } from "react"
import { Icon } from "@/shared/ui/icon"
import { Truncate } from "@/shared/ui/truncate"
import type { ComboboxItem, ComboboxSection, ComboboxText, TextRange } from "../model"
import styles from "./styles.module.css"

export type ComboboxListboxProps = {
  readonly ref: Ref<HTMLDivElement>
  readonly id: string
  readonly sections: readonly ComboboxSection[]
  readonly value: string
  readonly activeKey: string | null
  readonly optionId: (key: string) => string
  readonly text: ComboboxText
  readonly onActivate: (key: string) => void
  readonly onSelect: (value: string) => void
}

function Marked({ text, range }: { readonly text: string; readonly range?: TextRange }) {
  if (!range) return text
  const [start, end] = range
  return (
    <>
      {text.slice(0, start)}
      <mark className={styles.mark}>{text.slice(start, end)}</mark>
      {text.slice(end)}
    </>
  )
}

type OptionProps = Pick<
  ComboboxListboxProps,
  "value" | "activeKey" | "optionId" | "onActivate" | "onSelect"
> & { readonly item: ComboboxItem }

function Option({ item, value, activeKey, optionId, onActivate, onSelect }: OptionProps) {
  const { option } = item
  const selected = option.value === value
  const active = option.key === activeKey
  return (
    // biome-ignore lint/a11y/useKeyWithClickEvents: options take keys through the search field, which owns focus via aria-activedescendant
    <div
      id={optionId(option.key)}
      role="option"
      tabIndex={-1}
      aria-selected={selected}
      data-active={active || undefined}
      className={styles.option}
      onPointerMove={() => {
        if (!active) onActivate(option.key)
      }}
      onClick={() => onSelect(option.value)}
    >
      <span className={styles.text}>
        <Truncate className={styles.label}>
          <Marked text={option.label} range={item.label} />
        </Truncate>
        {option.detail ? (
          <Truncate className={styles.detail}>
            <Marked text={option.detail} range={item.detail} />
          </Truncate>
        ) : null}
      </span>
      <span className={styles.check}>{selected ? <Icon name="check" /> : null}</span>
    </div>
  )
}

export function ComboboxListbox(props: ComboboxListboxProps) {
  const { ref, id, sections, text, value, activeKey, optionId } = props
  const empty = sections.length === 0
  const renderItems = (items: readonly ComboboxItem[]) =>
    items.map((item) => (
      <Option
        key={item.option.key}
        item={item}
        value={value}
        activeKey={activeKey}
        optionId={optionId}
        onActivate={props.onActivate}
        onSelect={props.onSelect}
      />
    ))
  return (
    <>
      <div
        ref={ref}
        id={id}
        role="listbox"
        aria-label={text.label}
        className={styles.list}
        hidden={empty}
        onMouseDown={(event) => event.preventDefault()}
      >
        {sections.map((section) =>
          section.label ? (
            // biome-ignore lint/a11y/useSemanticElements: a listbox owns options and groups only, a fieldset is not allowed there
            <div
              key={section.key}
              role="group"
              aria-labelledby={`${id}-${section.key}`}
              className={styles.group}
            >
              <div id={`${id}-${section.key}`} className={styles.heading} data-heading="">
                {section.label}
              </div>
              {renderItems(section.items)}
            </div>
          ) : (
            <Fragment key={section.key}>{renderItems(section.items)}</Fragment>
          ),
        )}
      </div>
      <div role="status">
        {empty ? (
          <p className={styles.empty}>
            <span className={styles.emptyTitle}>{text.empty}</span>
            <span className={styles.hint}>{text.emptyHint}</span>
          </p>
        ) : null}
      </div>
    </>
  )
}
