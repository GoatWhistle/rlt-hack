import { clsx } from "clsx"
import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from "react"
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
export const SLOW_SEARCH_MS = 1000

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
  const [slow, setSlow] = useState(false)
  useAutoHeight(fieldRef, text)

  useEffect(() => {
    if (!search.isPending) {
      setSlow(false)
      return
    }
    const timer = window.setTimeout(() => setSlow(true), SLOW_SEARCH_MS)
    return () => window.clearTimeout(timer)
  }, [search.isPending])

  const error = problem ?? search.error
  const showCounter = text.length >= COUNTER_FROM
  const describedBy = [hintId, showCounter ? counterId : "", error ? errorId : ""]
    .filter(Boolean)
    .join(" ")

  function submit(value = text) {
    if (search.isPending) return
    const query = value.trim()
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
    submit(example)
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
          <span role="status" className={styles.progress}>
            {slow ? t("box.progress") : null}
          </span>
          <span id={hintId} className={clsx(styles.hint, slow && styles.hidden)}>
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
          <Button
            type="submit"
            className={styles.submit}
            aria-disabled={search.isPending}
            aria-busy={search.isPending}
          >
            {search.isPending ? (
              <span className={styles.spinner} aria-hidden="true" />
            ) : (
              <Icon name="search" />
            )}
            {t("box.submit")}
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
