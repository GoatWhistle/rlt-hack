export type ComboboxOption = {
  readonly key: string
  readonly value: string
  readonly label: string
  readonly detail?: string
  readonly keywords?: readonly string[]
}

export type ComboboxGroup = {
  readonly key: string
  readonly label?: string
  readonly options: readonly ComboboxOption[]
}

export type TextRange = readonly [start: number, end: number]

export type ComboboxItem = {
  readonly option: ComboboxOption
  readonly label?: TextRange
  readonly detail?: TextRange
}

export type ComboboxSection = {
  readonly key: string
  readonly label?: string
  readonly items: readonly ComboboxItem[]
}

export type ComboboxText = {
  readonly label: string
  readonly trigger: string
  readonly hint?: string
  readonly search: string
  readonly empty: string
  readonly emptyHint: string
  readonly close: string
}
