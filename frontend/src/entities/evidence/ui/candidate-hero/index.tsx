import { clsx } from "clsx"
import type { ReactNode } from "react"
import { Dot } from "@/shared/ui/dot"
import { FactRow } from "@/shared/ui/fact-row"
import styles from "./styles.module.css"

export type HeroFigure = {
  readonly value: string
  readonly label: string
  readonly note?: string
}

export type HeroPoint = {
  readonly key: string
  readonly label: string
  readonly text: string
}

export type HeroReason = {
  readonly title: string
  readonly text?: string
  readonly points?: readonly HeroPoint[]
}

export type CandidateHeroProps = {
  readonly name: string
  readonly role: string
  readonly code?: string
  readonly check: boolean
  readonly figure?: HeroFigure
  readonly verdict: ReactNode
  readonly reason?: HeroReason
  readonly pager?: ReactNode
  readonly children?: ReactNode
}

function Reason({ reason }: { readonly reason: HeroReason }) {
  return (
    <div className={styles.reason}>
      <h3 className={styles.reasonTitle}>{reason.title}</h3>
      {reason.points && reason.points.length > 0 ? (
        <ul className={styles.points}>
          {reason.points.map((point) => (
            <li key={point.key} className={styles.point}>
              <Dot shape="dashed" tone="warning" size="md" />
              <span>
                <strong className={styles.pointLabel}>{point.label}</strong>
                {" — "}
                {point.text}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.reasonText}>{reason.text}</p>
      )}
    </div>
  )
}

export function CandidateHero({
  name,
  role,
  code,
  check,
  figure,
  verdict,
  reason,
  pager,
  children,
}: CandidateHeroProps) {
  return (
    <div className={clsx(styles.hero, check && styles.check)}>
      {pager}
      <div className={styles.top}>
        <div className={styles.identity}>
          <h2 tabIndex={-1} className={styles.name}>
            {name}
          </h2>
          <p className={styles.meta}>
            <FactRow>
              <span>{role}</span>
              {code ? <span className={styles.code}>{code}</span> : null}
            </FactRow>
          </p>
        </div>
        {figure ? (
          <p className={styles.result}>
            <span className={styles.figure}>{figure.value}</span>
            <span className={styles.figureLabel}>{figure.label}</span>
            {figure.note ? <span className={styles.figureNote}>{figure.note}</span> : null}
          </p>
        ) : null}
      </div>
      <div className={styles.verdict}>{verdict}</div>
      {reason ? <Reason reason={reason} /> : null}
      {children}
    </div>
  )
}
