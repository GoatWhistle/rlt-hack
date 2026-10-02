import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import { useCompanyName } from "@/entities/evidence/labels"
import {
  type CellState,
  cellState,
  confirmedCell,
  coverageOf,
} from "@/entities/search/coverage"
import type { Candidate, QueryItem } from "@/entities/search/model"
import { Caption } from "@/shared/ui/caption"
import { Icon, type IconName } from "@/shared/ui/icon"
import { ScrollRegion } from "@/shared/ui/scroll-region"
import { CoverSetNote } from "../cover-set"
import styles from "./styles.module.css"

const MARKS: Record<CellState, IconName> = {
  offer: "check",
  registered: "fileCheck",
  assumed: "wave",
  history: "clock",
  conflict: "close",
  insufficient: "minus",
}

const LOOKS: Record<CellState, string | undefined> = {
  offer: styles.offer,
  registered: styles.registered,
  assumed: styles.assumed,
  history: styles.history,
  conflict: styles.conflict,
  insufficient: styles.insufficient,
}

export type CoverageMatrixProps = {
  readonly candidates: readonly Candidate[]
  readonly items: readonly QueryItem[]
  readonly onPick?: (candidateId: string, itemId: string) => void
}

export function CoverageMatrix({ candidates, items, onPick }: CoverageMatrixProps) {
  const { t } = useTranslation("search")
  const nameOf = useCompanyName()
  return (
    <div className={styles.matrix}>
      <ScrollRegion label={t("coverage.title")}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">{t("coverage.company")}</th>
              {items.map((item) => (
                <th key={item.id} scope="col" className={styles.item}>
                  {item.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => {
              const summary = coverageOf(candidate, items)
              return (
                <tr key={candidate.id}>
                  <th scope="row" className={styles.company}>
                    <span>{nameOf(candidate)}</span>
                    <span className={styles.summary}>{t("coverage.summary", summary)}</span>
                  </th>
                  {items.map((item) => {
                    const state = cellState(candidate, item.id)
                    const label = t(`coverage.state.${state}`)
                    const strong = confirmedCell(candidate, item.id)
                    const content = (
                      <>
                        <Icon name={MARKS[state]} size="sm" />
                        <span>{strong ? t("coverage.confirmed") : label}</span>
                      </>
                    )
                    return (
                      <td key={item.id} className={clsx(styles.cell, LOOKS[state])}>
                        {onPick ? (
                          <button
                            type="button"
                            className={styles.pick}
                            onClick={() => onPick(candidate.id, item.id)}
                            aria-label={t("coverage.open", {
                              company: nameOf(candidate),
                              item: item.name,
                              state: label,
                            })}
                          >
                            {content}
                          </button>
                        ) : (
                          content
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollRegion>
      <CoverSetNote candidates={candidates} items={items} />
      <Caption>{t("coverage.legend")}</Caption>
      <Caption>{t("coverage.conditions")}</Caption>
    </div>
  )
}
