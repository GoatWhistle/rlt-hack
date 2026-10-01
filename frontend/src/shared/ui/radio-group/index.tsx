import { useId } from "react"
import styles from "./styles.module.css"

export type RadioOption<T extends string> = {
  readonly value: T
  readonly label: string
}

export type RadioGroupProps<T extends string> = {
  readonly legend: string
  readonly options: readonly RadioOption<T>[]
  readonly value: T
  readonly onChange: (value: T) => void
}

export function RadioGroup<T extends string>({
  legend,
  options,
  value,
  onChange,
}: RadioGroupProps<T>) {
  const name = useId()
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className={styles.option}>
          <input
            type="radio"
            className={styles.input}
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </fieldset>
  )
}
