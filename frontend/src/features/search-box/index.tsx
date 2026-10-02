import { clsx } from "clsx"
import { type FormEvent, useId, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { DEFAULT_REGION_CODE } from "@/entities/evidence/regions"
import { FOCUS_SHORTCUT } from "@/shared/keyboard/use-focus-shortcut"
import { Icon } from "@/shared/ui/icon"
import { COUNTER_FROM, FieldBar, SubmitButton } from "./field-bar"
import { isInputProblem, joinIds, useFieldEffects, useReportStage } from "./field-effects"
import { RegionPreference } from "./region-preference"
import { SearchError } from "./search-error"
import { SweepBar } from "./stage-line"
import styles from "./styles.module.css"
import { useAutoHeight } from "./use-auto-height"
import { type Attachment, type Found, isBlocked, useSearchSubmit } from "./use-search-submit"
import { type SearchStage, useStage } from "./use-stage"

export { COUNTER_FROM } from "./field-bar"
export { FINE_POINTER, isInputProblem } from "./field-effects"
export { StageLine } from "./stage-line"
export type { Attachment } from "./use-search-submit"
export type { SearchStage } from "./use-stage"

export type SearchBoxProps = {
  readonly initialRegion?: string
  readonly initialText?: string
  readonly compact?: boolean
  readonly inputId?: string
  readonly autoFocus?: boolean
  readonly shortcut?: boolean
  readonly attachment?: Attachment
  readonly onStage?: (stage: SearchStage | null) => void
  readonly onFound: Found
}

function DropNote({ shown }: { readonly shown: boolean }) {
  const { t } = useTranslation("search")
  return (
    <span className={styles.drop} aria-hidden={!shown}>
      <Icon name="upload" />
      {t("box.drop")}
    </span>
  )
}

function useFieldCopy(attachment: Attachment | undefined) {
  const { t } = useTranslation("search")
  return attachment?.upload != null
    ? { label: t("box.noteLabel"), placeholder: t("box.notePlaceholder") }
    : { label: t("box.label"), placeholder: t("box.placeholder") }
}

function AttachmentChip({ attachment }: { readonly attachment: Attachment | undefined }) {
  if (!attachment) return null
  return (
    <>
      <div className={styles.chip}>{attachment.chip}</div>
      <DropNote shown={attachment.dropping} />
    </>
  )
}

export function SearchBox({
  initialText = "",
  initialRegion = DEFAULT_REGION_CODE,
  compact = false,
  inputId,
  autoFocus,
  shortcut,
  attachment,
  onStage,
  onFound,
}: SearchBoxProps) {
  const search = useSearchSubmit(attachment, onFound)
  const [text, setText] = useState(initialText)
  const [region, setRegion] = useState(initialRegion)
  const fieldRef = useRef<HTMLTextAreaElement>(null)
  const ownId = useId()
  const fieldId = inputId ?? ownId
  const counterId = useId()
  const errorId = useId()
  const stage = useStage(search.pending)
  useAutoHeight(fieldRef, text)
  useFieldEffects(fieldRef, { autoFocus: autoFocus === true, shortcut: shortcut === true })
  useReportStage(stage, onStage)

  const { error } = search
  const invalid = isInputProblem(error)
  const showCounter = text.length >= COUNTER_FROM
  const describedBy = joinIds([showCounter ? counterId : "", error ? errorId : ""])
  const copy = useFieldCopy(attachment)
  const submitButton = (
    <SubmitButton pending={search.pending} blocked={isBlocked(attachment, text)} />
  )
  const submit = () => search.submit(text, region)

  function change(next: string) {
    setText(next)
    search.clear()
  }

  return (
    <form
      className={clsx(styles.box, compact && styles.compact)}
      noValidate
      aria-busy={search.pending}
      onSubmit={(event: FormEvent) => {
        event.preventDefault()
        submit()
      }}
    >
      {compact ? null : (
        <label htmlFor={fieldId} className={styles.label}>
          {copy.label}
        </label>
      )}
      <div
        className={clsx(styles.field, invalid && styles.invalid)}
        data-dropping={attachment?.dropping || undefined}
      >
        <textarea
          id={fieldId}
          ref={fieldRef}
          className={styles.input}
          data-part="query-text"
          rows={compact ? 1 : 4}
          value={text}
          placeholder={copy.placeholder}
          aria-label={compact ? copy.label : undefined}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          aria-keyshortcuts={shortcut ? FOCUS_SHORTCUT : undefined}
          onChange={(event) => change(event.target.value)}
        />
        <AttachmentChip attachment={attachment} />
        <FieldBar
          region={
            <span className={styles.tools}>
              {attachment?.tool}
              <RegionPreference
                collapse={compact}
                value={region}
                onChange={setRegion}
                disabled={search.pending}
              />
            </span>
          }
          compact={compact}
          stage={stage}
          counterId={counterId}
          length={text.length}
          submit={submitButton}
        />
        {search.pending ? <SweepBar /> : null}
      </div>
      {attachment ? <p className={styles.hint}>{attachment.hint}</p> : null}
      <div className={styles.status}>
        <SearchError id={errorId} error={error} onRetry={submit} />
      </div>
    </form>
  )
}
