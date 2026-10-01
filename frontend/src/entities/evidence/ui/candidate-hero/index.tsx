import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type HeroFigure = {
  readonly value: string
  readonly label: string
  readonly note?: string
}

export type HeroReason = {
  readonly title: string
  readonly text: string
}

export type CandidateHeroProps = {
  readonly name: string
  readonly role: string
  readonly code?: string
  readonly check: boolean
  readonly figure?: HeroFigure
  readonly verdict: ReactNode
  readonly reason?: HeroReason
  readonly children?: ReactNode
}

export function CandidateHero({
  name,
  role,
  code,
  check,
  figure,
  verdict,
  reason,
  children,
}: CandidateHeroProps) {
  return (
    <div className={clsx(styles.hero, check && styles.check)}>
      <div className={styles.top}>
        <div className={styles.identity}>
          <h2 tabIndex={-1} className={styles.name}>
            {name}
          </h2>
          <p className={styles.meta}>
            {role}
            {code ? (
              <>
                {" · "}
                <span className={styles.code}>{code}</span>
              </>
            ) : null}
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
      {reason ? (
        <div className={styles.reason}>
          <h3 className={styles.reasonTitle}>{reason.title}</h3>
          <p className={styles.reasonText}>{reason.text}</p>
        </div>
      ) : null}
      {children}
    </div>
  )
}
