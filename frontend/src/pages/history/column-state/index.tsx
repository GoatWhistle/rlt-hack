import { useTranslation } from "react-i18next"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { LoadingState } from "@/shared/ui/loading-state"
import { Bone } from "@/shared/ui/skeleton"
import { TextButton } from "@/shared/ui/text-button"
import styles from "./styles.module.css"

const ROWS = ["first", "second", "third", "fourth"]

export function ColumnLoading() {
  const { t } = useTranslation("history")
  return (
    <LoadingState label={t("loading")}>
      <ul className={styles.rows} aria-hidden="true">
        {ROWS.map((row) => (
          <li key={row} className={styles.row}>
            <Bone className={styles.title} />
            <Bone className={styles.meta} />
          </li>
        ))}
      </ul>
    </LoadingState>
  )
}

export type ColumnErrorProps = {
  readonly error: unknown
  readonly onRetry: () => void
}

export function ColumnError({ error, onRetry }: ColumnErrorProps) {
  const { t } = useTranslation("history")
  const message = useErrorMessage()
  return (
    <div className={styles.problem} role="alert">
      <span>{message(error)}</span>
      <TextButton onClick={onRetry}>{t("retry")}</TextButton>
    </div>
  )
}
