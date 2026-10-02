import { useState } from "react"
import { useTranslation } from "react-i18next"
import { usePresence } from "@/shared/motion/use-presence"
import { Icon } from "@/shared/ui/icon"
import { TextButton } from "@/shared/ui/text-button"
import { FileNote } from "../file-note"
import { extensionOf, type Intake, sizeOf, splitName } from "../model"
import styles from "./styles.module.css"

function FileSize({ bytes }: { readonly bytes: number }) {
  const { t } = useTranslation("uploads")
  const { unit, value } = sizeOf(bytes)
  return <span className={styles.size}>{t(`intake.size.${unit}`, { size: value })}</span>
}

export type FileChipProps = {
  readonly intake: Intake | null
  readonly onRemove: () => void
  readonly onReplace: () => void
}

export function FileChip({ intake, onRemove, onReplace }: FileChipProps) {
  const { t } = useTranslation("uploads")
  const [shown, setShown] = useState(intake)
  if (intake && intake !== shown) setShown(intake)
  const presence = usePresence(intake !== null)
  if (!presence.isMounted || !shown) return null
  const { file } = shown
  const [head, tail] = splitName(file.name)
  const extension = extensionOf(file.name).toUpperCase()
  return (
    <div
      className={styles.chip}
      data-state={presence.state}
      inert={intake === null}
      onAnimationEnd={presence.onAnimationEnd}
    >
      <div className={styles.file}>
        <span className={styles.type}>
          <Icon name="file" />
          {extension ? <span className={styles.extension}>{extension}</span> : null}
        </span>
        <span className={styles.name} title={file.name}>
          <span className={styles.head}>{head}</span>
          <span className={styles.tail}>{tail}</span>
        </span>
        <FileSize bytes={file.size} />
        <TextButton
          className={styles.remove}
          aria-label={t("intake.removeLabel", { name: file.name })}
          onClick={onRemove}
        >
          <Icon name="close" size="sm" />
          {t("intake.remove")}
        </TextButton>
      </div>
      <FileNote intake={shown} onReplace={onReplace} />
    </div>
  )
}
