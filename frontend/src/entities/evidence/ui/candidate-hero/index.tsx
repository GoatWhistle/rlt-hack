import { clsx } from "clsx"
import type { ReactNode } from "react"
import styles from "./styles.module.css"

export type CandidateHeroProps = {
  readonly name: string
  readonly role: string
  readonly code?: string
  readonly check: boolean
  readonly figure?: { readonly value: string; readonly label: string }
  readonly verdict: ReactNode
  readonly children?: ReactNode
}

export function CandidateHero({
  name,
  role,
  code,
  check,
  figure,
  verdict,
  children,
}: CandidateHeroProps) {
  return (
    <div className={clsx(styles.hero, check && styles.check)}>
      <div className={styles.top}>
        <div className={styles.identity}>
          <h2 className={styles.name}>{name}</h2>
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
          </p>
        ) : null}
      </div>
      <div className={styles.verdict}>{verdict}</div>
      {children}
    </div>
  )
}
