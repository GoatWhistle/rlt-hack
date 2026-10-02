import { clsx } from "clsx"
import {
  type CSSProperties,
  type ReactElement,
  type ReactNode,
  type RefObject,
  useId,
  useRef,
  useState,
} from "react"
import { PaneFoldProvider, PaneRail } from "@/shared/ui/pane-fold"
import { SegmentedControl } from "@/shared/ui/segmented-control"
import styles from "./styles.module.css"
import { type FoldablePane, usePaneFolds } from "./use-pane-folds"
import { PANE_HEADING, WORKSPACE_VIEWS, type WorkspaceView } from "./use-workspace-view"

export { PANE_FOLDS_KEY } from "./use-pane-folds"
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
  readonly counts?: Readonly<Partial<Record<FoldablePane, number>>>
  readonly view: WorkspaceView
  readonly onShow: (view: WorkspaceView) => void
  readonly stackRef: RefObject<HTMLDivElement | null>
}

export function WorkspaceLayout({
  narrow,
  legend,
  labels,
  panes,
  counts,
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
  return <WorkspaceColumns labels={labels} panes={panes} counts={counts} />
}

type WorkspaceColumnsProps = Pick<WorkspaceLayoutProps, "labels" | "panes" | "counts">

function WorkspaceColumns({ labels, panes, counts }: WorkspaceColumnsProps) {
  const base = useId()
  const rails = useRef<Partial<Record<FoldablePane, HTMLButtonElement | null>>>({})
  const paneId = (pane: FoldablePane) => `${base}-${pane}`
  const [folds, change] = usePaneFolds((pane, folded) => {
    if (folded) rails.current[pane]?.focus()
    else
      document.getElementById(paneId(pane))?.querySelector<HTMLElement>(PANE_HEADING)?.focus()
  })
  const column = (pane: FoldablePane, className?: string) => (
    <>
      <div
        id={paneId(pane)}
        className={clsx(styles.pane, className)}
        data-pane={pane}
        data-folded={folds[pane] || undefined}
      >
        <PaneFoldProvider
          value={{
            label: labels[pane],
            controls: paneId(pane),
            onFold: () => change(pane, true),
          }}
        >
          {panes[pane]}
        </PaneFoldProvider>
      </div>
      {folds[pane] ? (
        <PaneRail
          ref={(node) => {
            rails.current[pane] = node
          }}
          pane={pane}
          label={labels[pane]}
          count={counts?.[pane]}
          controls={paneId(pane)}
          onUnfold={() => change(pane, false)}
        />
      ) : null}
    </>
  )
  return (
    <div
      className={styles.columns}
      data-list={folds.list ? "folded" : undefined}
      data-candidates={folds.candidates ? "folded" : undefined}
    >
      {column("list", styles.list)}
      {column("candidates")}
      <div className={clsx(styles.pane, styles.detail)} data-pane="evidence">
        {panes.evidence}
      </div>
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
