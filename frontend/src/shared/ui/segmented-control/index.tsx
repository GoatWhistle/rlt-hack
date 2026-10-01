import { useId } from "react"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import styles from "./styles.module.css"

export type SegmentedOption<T extends string> = {
  readonly value: T
  readonly label: string
  readonly description?: string
  readonly count?: number
}

export type SegmentedControlProps<T extends string> = {
  readonly legend: string
  readonly options: readonly SegmentedOption<T>[]
  readonly value: T
  readonly onChange: (value: T) => void
}

export function SegmentedControl<T extends string>({
  legend,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  const name = useId()
  return (
    <fieldset className={styles.group}>
      <VisuallyHidden as="legend">{legend}</VisuallyHidden>
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
