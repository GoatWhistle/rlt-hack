import { clsx } from "clsx"
import { type CSSProperties, type ReactElement, type ReactNode, type RefObject, useState } from "react"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import styles from "./styles.module.css"
import { WORKSPACE_VIEWS, type WorkspaceView } from "./use-workspace-view"

export {
  DEFAULT_VIEW,
  NARROW_LAYOUT,
  parseView,
  useWorkspaceView,
  viewParam,
  WORKSPACE_VIEWS,
  type WorkspaceView,
} from "./use-workspace-view"

export type WorkspaceLayoutProps = {
  readonly narrow: boolean
  readonly legend: string
  readonly labels: Readonly<Record<WorkspaceView, string>>
  readonly panes: Readonly<Record<WorkspaceView, ReactElement>>
  readonly view: WorkspaceView
  readonly onShow: (view: WorkspaceView) => void
  readonly stackRef: RefObject<HTMLDivElement | null>
}

export function WorkspaceLayout({
  narrow,
  legend,
  labels,
  panes,
  view,
  onShow,
  stackRef,
}: WorkspaceLayoutProps) {
  const [shown, setShown] = useState({ view, direction: 0 })
  if (shown.view !== view) {
    const step = WORKSPACE_VIEWS.indexOf(view) - WORKSPACE_VIEWS.indexOf(shown.view)
    setShown({ view, direction: Math.sign(step) })
  }
  if (narrow) {
    const slide = { "--slide-direction": shown.direction } as CSSProperties
    return (
      <div className={styles.stacked} ref={stackRef}>
        <div className={styles.switcher}>
          <SegmentedControl
            block
            legend={legend}
            value={view}
            onChange={onShow}
            options={WORKSPACE_VIEWS.map((value) => ({ value, label: labels[value] }))}
          />
        </div>
        <div
          key={view}
          className={styles.view}
          data-direction={shown.direction === 0 ? undefined : shown.direction}
          style={slide}
        >
          {panes[view]}
        </div>
      </div>
    )
  }
  return (
    <div className={styles.columns}>
      <div className={clsx(styles.pane, styles.list)}>{panes.list}</div>
      <div className={styles.pane}>{panes.candidates}</div>
      <div className={clsx(styles.pane, styles.detail)}>{panes.evidence}</div>
    </div>
  )
}

export type WorkspaceEmptyProps = {
  readonly list: ReactNode
  readonly children: ReactNode
}

export function WorkspaceEmpty({ list, children }: WorkspaceEmptyProps) {
  return (
    <div className={styles.empty}>
      {list}
      {children}
    </div>
  )
}
