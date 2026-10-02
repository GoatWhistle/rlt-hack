import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Icon } from "@/shared/ui/icon"
import { Spinner } from "@/shared/ui/spinner"
import { TextButton } from "@/shared/ui/text-button"
import { type Intake, MAX_FILE_MB } from "../model"
import styles from "./styles.module.css"

type Tone = "quiet" | "warning"

type Note = {
  readonly tone: Tone
  readonly text: string
  readonly mark: ReactNode
  readonly role?: "alert" | "status"
  readonly replace: boolean
}

function useNote(intake: Intake): Note | null {
  const { t } = useTranslation("uploads")
  const { t: notices } = useTranslation("notices")
  const warning = <Icon name="warning" size="sm" tone="warning" />
  switch (intake.status) {
    case "reading":
      return {
        tone: "quiet",
        text: t("intake.reading"),
        mark: <Spinner />,
        role: "status",
        replace: false,
      }
    case "later":
      return {
        tone: "quiet",
        text: t("intake.later"),
        mark: <Icon name="clock" size="sm" />,
        replace: false,
      }
    case "rejected":
      return {
        tone: "warning",
        text: t(`intake.rejected.${intake.reason}`, { limit: MAX_FILE_MB }),
        mark: warning,
        role: "alert",
        replace: true,
      }
    case "checked":
      if (!intake.check.ok) {
        return {
          tone: "warning",
          text: notices(`problem.${intake.check.problem}.title`),
          mark: warning,
          replace: true,
        }
      }
      if (intake.check.notices.length > 0) return null
      return {
        tone: "warning",
        text: t("intake.noValid"),
        mark: warning,
        role: "alert",
        replace: true,
      }
  }
}

export type FileNoteProps = {
  readonly intake: Intake
  readonly onReplace: () => void
}

export function FileNote({ intake, onReplace }: FileNoteProps) {
  const { t } = useTranslation("uploads")
  const note = useNote(intake)
  if (!note) return null
  return (
    <div className={styles.note} data-tone={note.tone}>
      <p role={note.role} className={styles.text}>
        <span className={styles.mark}>{note.mark}</span>
        {note.text}
      </p>
      {note.replace ? (
        <TextButton className={styles.replace} onClick={onReplace}>
          {t("intake.replace")}
        </TextButton>
      ) : null}
    </div>
  )
}
