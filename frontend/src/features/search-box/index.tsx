import { clsx } from "clsx"
import { type FormEvent, useId, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { DEFAULT_LIMIT, MAX_QUERY_LENGTH, type SearchResult } from "@/entities/search/model"
import { useRunSearch } from "@/entities/search/queries"
import { FOCUS_SHORTCUT } from "@/shared/keyboard/use-focus-shortcut"
import { useMediaQuery } from "@/shared/media/use-media-query"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { KeyHint } from "@/shared/ui/key-hint"
import { Spinner } from "@/shared/ui/spinner"
import { ExampleChips } from "./example-chips"
import {
  isInputProblem,
  joinIds,
  problemOf,
  useFieldEffects,
  useReportStage,
  wantsSubmit,
} from "./field-effects"
import { SearchError } from "./search-error"
import { StageLine, SweepBar } from "./stage-line"
import styles from "./styles.module.css"
import { useAutoHeight } from "./use-auto-height"
import { type SearchStage, useStage } from "./use-stage"

export { FINE_POINTER, isInputProblem } from "./field-effects"
export { StageLine } from "./stage-line"
export type { SearchStage } from "./use-stage"

export const COUNTER_FROM = 3600
export const PICK_TO_FIELD = "(max-width: 47.99rem)"

export type SearchBoxProps = {
  readonly initialText?: string
  readonly showExamples?: boolean
  readonly compact?: boolean
  readonly inputId?: string
  readonly autoFocus?: boolean
  readonly shortcut?: boolean
  readonly onStage?: (stage: SearchStage | null) => void
  readonly onFound: (result: SearchResult) => void
}

type FieldBarProps = {
  readonly compact: boolean
  readonly stage: SearchStage | null
  readonly hintId: string
  readonly counterId: string
  readonly length: number
  readonly pending: boolean
  readonly shortcut: boolean
}

function FieldBar(props: FieldBarProps) {
  const { compact, stage, hintId, counterId, length, pending, shortcut } = props
  const { t } = useTranslation("search")
  return (
    <div className={styles.bar}>
      {compact ? null : <StageLine stage={stage} />}
      {stage || compact ? null : (
        <span id={hintId} className={styles.hint}>
          {t("box.hint")}
        </span>
      )}
      {length >= COUNTER_FROM ? (
        <span
          id={counterId}
          className={clsx(styles.counter, length > MAX_QUERY_LENGTH && styles.over)}
        >
          {t("box.counter", { count: length, limit: MAX_QUERY_LENGTH })}
        </span>
      ) : null}
      {shortcut && !pending ? <KeyHint keys={FOCUS_SHORTCUT} className={styles.key} /> : null}
      <Button
        type="submit"
        className={styles.submit}
        aria-disabled={pending}
        aria-busy={pending}
      >
        {pending ? <Spinner /> : <Icon name="search" />}
        {t("box.submit")}
      </Button>
    </div>
  )
}

export function SearchBox({
  initialText = "",
  showExamples = true,
  compact = false,
  inputId,
  autoFocus,
  shortcut,
  onStage,
  onFound,
}: SearchBoxProps) {
  const { t } = useTranslation("search")
  const search = useRunSearch()
  const [text, setText] = useState(initialText)
  const [problem, setProblem] = useState<unknown>(null)
  const fieldRef = useRef<HTMLTextAreaElement>(null)
  const ownId = useId()
  const fieldId = inputId ?? ownId
  const hintId = useId()
  const counterId = useId()
  const errorId = useId()
  const pickToField = useMediaQuery(PICK_TO_FIELD)
  const stage = useStage(search.isPending)
  useAutoHeight(fieldRef, text)
  useFieldEffects(fieldRef, { autoFocus: autoFocus === true, shortcut: shortcut === true })
  useReportStage(stage, onStage)

  const error = problem ?? search.error
  const invalid = isInputProblem(error)
  const showCounter = text.length >= COUNTER_FROM
  const describedBy = joinIds([
    compact ? "" : hintId,
    showCounter ? counterId : "",
    error ? errorId : "",
  ])

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
    if (search.isPending) return
    change(example)
    if (pickToField) {
      fieldRef.current?.focus()
      return
    }
    submit(example)
  }

  return (
    <form
      className={clsx(styles.box, compact && styles.compact)}
      noValidate
      aria-busy={search.isPending}
      onSubmit={(event: FormEvent) => {
        event.preventDefault()
        submit()
      }}
    >
      {compact ? null : (
        <label htmlFor={fieldId} className={styles.label}>
          {t("box.label")}
        </label>
      )}
      <div className={clsx(styles.field, invalid && styles.invalid)}>
        <textarea
          id={fieldId}
          ref={fieldRef}
          className={styles.input}
          rows={compact ? 1 : 2}
          value={text}
          placeholder={t("box.placeholder")}
          aria-label={compact ? t("box.label") : undefined}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          aria-keyshortcuts={shortcut ? FOCUS_SHORTCUT : undefined}
          onChange={(event) => change(event.target.value)}
          onKeyDown={(event) => {
            if (!wantsSubmit(event)) return
            event.preventDefault()
            submit()
          }}
        />
        <FieldBar
          compact={compact}
          stage={stage}
          hintId={hintId}
          counterId={counterId}
          length={text.length}
          pending={search.isPending}
          shortcut={shortcut === true}
        />
        {search.isPending ? <SweepBar /> : null}
      </div>
      <SearchError id={errorId} error={error} onRetry={() => submit()} />
      {showExamples ? <ExampleChips disabled={search.isPending} onPick={pick} /> : null}
    </form>
  )
}
