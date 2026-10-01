import { clsx } from "clsx"
import { type FormEvent, type KeyboardEvent, useId, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { invalidQuery } from "@/entities/search/gateway"
import { DEFAULT_LIMIT, MAX_QUERY_LENGTH, type SearchResult } from "@/entities/search/model"
import { useRunSearch } from "@/entities/search/queries"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { ExampleChips } from "./example-chips"
import styles from "./styles.module.css"
import { useAutoHeight } from "./use-auto-height"

export const COUNTER_FROM = 3600

export type SearchBoxProps = {
  readonly initialText?: string
  readonly showExamples?: boolean
  readonly onFound: (result: SearchResult) => void
}

function problemOf(text: string) {
  if (!text) return invalidQuery("empty_query")
  if (text.length > MAX_QUERY_LENGTH) return invalidQuery("query_too_long")
  return null
}

function wantsSubmit(event: KeyboardEvent<HTMLTextAreaElement>): boolean {
  if (event.key !== "Enter" || event.nativeEvent.isComposing) return false
  return event.metaKey || event.ctrlKey || !event.shiftKey
}

export function SearchBox({ initialText = "", showExamples = true, onFound }: SearchBoxProps) {
  const { t } = useTranslation("search")
  const errorMessage = useErrorMessage()
  const search = useRunSearch()
  const [text, setText] = useState(initialText)
  const [problem, setProblem] = useState<unknown>(null)
  const fieldRef = useRef<HTMLTextAreaElement>(null)
  const fieldId = useId()
  const hintId = useId()
  const counterId = useId()
  const errorId = useId()
  useAutoHeight(fieldRef, text)

  const error = problem ?? search.error
  const showCounter = text.length >= COUNTER_FROM
  const describedBy = [hintId, showCounter ? counterId : "", error ? errorId : ""]
    .filter(Boolean)
    .join(" ")

  function submit() {
    if (search.isPending) return
    const query = text.trim()
    const found = problemOf(query)
    setProblem(found)
    if (found) return
    search.mutate(
      { text: query, limit: DEFAULT_LIMIT },
      { onSuccess: (result) => onFound(result) },
    )
  }

  function change(next: string) {
    setText(next)
    setProblem(null)
    if (search.isError) search.reset()
  }

  function pick(example: string) {
    change(example)
    fieldRef.current?.focus()
  }

  return (
    <form
      className={styles.box}
      noValidate
      aria-busy={search.isPending}
      onSubmit={(event: FormEvent) => {
        event.preventDefault()
        submit()
      }}
    >
      <label htmlFor={fieldId} className={styles.label}>
        {t("box.label")}
      </label>
      <div className={clsx(styles.field, error ? styles.invalid : undefined)}>
        <textarea
          id={fieldId}
          ref={fieldRef}
          className={styles.input}
          rows={2}
          value={text}
          placeholder={t("box.placeholder")}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => change(event.target.value)}
          onKeyDown={(event) => {
            if (!wantsSubmit(event)) return
            event.preventDefault()
            submit()
          }}
        />
        <div className={styles.bar}>
          <span id={hintId} className={styles.hint}>
            {t("box.hint")}
          </span>
          {showCounter ? (
            <span
              id={counterId}
              className={clsx(styles.counter, text.length > MAX_QUERY_LENGTH && styles.over)}
            >
              {t("box.counter", { count: text.length, limit: MAX_QUERY_LENGTH })}
            </span>
          ) : null}
          <Button type="submit" className={styles.submit} aria-disabled={search.isPending}>
            <Icon name="search" />
            {search.isPending ? t("box.pending") : t("box.submit")}
          </Button>
        </div>
      </div>
      {error ? (
        <p id={errorId} role="alert" className={styles.error}>
          <Icon name="warning" size="sm" />
          {errorMessage(error)}
        </p>
      ) : null}
      {showExamples ? <ExampleChips onPick={pick} /> : null}
    </form>
  )
}
