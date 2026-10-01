import { clsx } from "clsx"
import { useId, useRef } from "react"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"
import { useThumb } from "./use-thumb"

export type SegmentedOption<T extends string> = {
  readonly value: T
  readonly label: string
  readonly description?: string
  readonly count?: string
}

export type SegmentedControlProps<T extends string> = {
  readonly legend: string
  readonly options: readonly SegmentedOption<T>[]
  readonly value: T
  readonly onChange: (value: T) => void
  readonly scroll?: boolean
  readonly block?: boolean
}

export function SegmentedControl<T extends string>({
  legend,
  options,
  value,
  onChange,
  scroll = false,
  block = false,
}: SegmentedControlProps<T>) {
  const name = useId()
  const ref = useRef<HTMLFieldSetElement>(null)
  useThumb(ref, value)
  return (
    <fieldset
      ref={ref}
      className={clsx(styles.group, scroll && styles.scroll, block && styles.block)}
    >
      <VisuallyHidden as="legend">{legend}</VisuallyHidden>
      <span className={styles.thumb} aria-hidden="true" data-thumb-layer />
      {options.map((option) => (
        <label key={option.value} className={styles.option}>
          <input
            className={styles.input}
            type="radio"
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          <span aria-hidden={option.description ? true : undefined}>{option.label}</span>
          {option.count === undefined ? null : (
            <span className={styles.count}>{option.count}</span>
          )}
          {option.description ? <VisuallyHidden>{option.description}</VisuallyHidden> : null}
        </label>
      ))}
    </fieldset>
  )
}
