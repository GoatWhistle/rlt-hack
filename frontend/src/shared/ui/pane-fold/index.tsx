import { createContext, type ReactNode, type Ref, useContext } from "react"
import { useTranslation } from "react-i18next"
import { CountBadge } from "@/shared/ui/count-badge"
import { Icon } from "@/shared/ui/icon"
import { ToolButton } from "@/shared/ui/tool-button"
import styles from "./styles.module.css"

export type PaneFoldControl = {
  readonly label: string
  readonly controls: string
  readonly onFold: () => void
}

const PaneFoldContext = createContext<PaneFoldControl | null>(null)

export function PaneFoldProvider({
  value,
  children,
}: {
  readonly value: PaneFoldControl | null
  readonly children: ReactNode
}) {
  return <PaneFoldContext value={value}>{children}</PaneFoldContext>
}

export function usePaneFold(): PaneFoldControl | null {
  return useContext(PaneFoldContext)
}

export function PaneFold({ control }: { readonly control: PaneFoldControl }) {
  const { t } = useTranslation()
  const name = t("workspace.fold", { name: control.label })
  return (
    <ToolButton
      className={styles.fold}
      aria-controls={control.controls}
      aria-label={name}
      title={name}
      onClick={control.onFold}
    >
      <Icon name="fold" />
    </ToolButton>
  )
}

export type PaneRailProps = {
  readonly label: string
  readonly count?: number
  readonly controls: string
  readonly pane: string
  readonly ref?: Ref<HTMLButtonElement>
  readonly onUnfold: () => void
}

export function PaneRail({ label, count, controls, pane, ref, onUnfold }: PaneRailProps) {
  const { t } = useTranslation()
  return (
    <button
      ref={ref}
      type="button"
      className={styles.rail}
      data-pane={pane}
      aria-expanded={false}
      aria-controls={controls}
      aria-label={t("workspace.unfold", { name: label })}
      onClick={onUnfold}
    >
      <span className={styles.open} aria-hidden="true">
        <Icon name="fold" />
      </span>
      <span className={styles.label}>{label}</span>
      {count === undefined ? null : <CountBadge value={count} />}
    </button>
  )
}
