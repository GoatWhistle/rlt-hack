import { useTranslation } from "react-i18next"
import { useErrorMessage } from "@/shared/errors/use-error-message"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import { isInputProblem } from "../field-effects"
import styles from "./styles.module.css"

export type SearchErrorProps = {
  readonly id: string
  readonly error: unknown
  readonly onRetry: () => void
}

export function SearchError({ id, error, onRetry }: SearchErrorProps) {
  const { t } = useTranslation()
  const errorMessage = useErrorMessage()
  if (!error) return null
  const input = isInputProblem(error)
  return (
    <div className={styles.row}>
      <p id={id} role="alert" className={styles.error} data-input={input || undefined}>
        <Icon name="warning" size="sm" />
        {errorMessage(error)}
      </p>
      {input ? null : (
        <TextButton className={styles.retry} onClick={onRetry}>
          {t("action.retry")}
        </TextButton>
      )}
    </div>
  )
}
