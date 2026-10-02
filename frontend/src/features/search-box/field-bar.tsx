import { clsx } from "clsx"
import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { MAX_QUERY_LENGTH } from "@/entities/search/model"
import { Button } from "@/shared/ui/button"
import { Icon } from "@/shared/ui/icon"
import { Spinner } from "@/shared/ui/spinner"
import { StageLine } from "./stage-line"
import styles from "./styles.module.css"
import type { SearchStage } from "./use-stage"

export const COUNTER_FROM = 3600

export type SubmitButtonProps = {
  readonly pending: boolean
  readonly blocked: boolean
}

export function SubmitButton({ pending, blocked }: SubmitButtonProps) {
  const { t } = useTranslation("search")
  return (
    <Button
      type="submit"
      className={styles.submit}
      aria-disabled={pending || blocked}
      aria-busy={pending}
    >
      {pending ? <Spinner /> : <Icon name="search" />}
      {t("box.submit")}
    </Button>
  )
}

export type FieldBarProps = {
  readonly region: ReactNode
  readonly compact: boolean
  readonly stage: SearchStage | null
  readonly counterId: string
  readonly length: number
  readonly submit: ReactNode
}

export function FieldBar(props: FieldBarProps) {
  const { region, compact, stage, counterId, length, submit } = props
  const { t } = useTranslation("search")
  return (
    <div className={styles.bar} data-part="query-bar">
      {region}
      {compact ? null : <StageLine stage={stage} />}
      {length >= COUNTER_FROM ? (
        <span
          id={counterId}
          className={clsx(styles.counter, length > MAX_QUERY_LENGTH && styles.over)}
        >
          {t("box.counter", { count: length, limit: MAX_QUERY_LENGTH })}
        </span>
      ) : null}
      {submit}
    </div>
  )
}
