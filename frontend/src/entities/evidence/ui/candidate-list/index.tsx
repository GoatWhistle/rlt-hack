import {
  type AnimationEvent,
  type KeyboardEvent,
  type ReactNode,
  useRef,
  useState,
} from "react"
import { useTranslation } from "react-i18next"
import { type CandidateView, type ItemView, matchFor } from "@/entities/evidence/view"
import { Caption } from "@/shared/ui/caption"
import { FilterNote } from "@/shared/ui/filter-note"
import { ResultSection } from "@/shared/ui/result-section"
import { TextButton } from "@/shared/ui/text-button"
import { CandidateCard } from "../candidate-card"
import styles from "./styles.module.css"

export const VISIBLE_CANDIDATES = 5
export const REVEAL_LIMIT = 5
export const REVEAL_ANIMATION = "reveal-x"

const NEXT_KEYS = new Set(["ArrowDown", "j", "J"])
const PREV_KEYS = new Set(["ArrowUp", "k", "K"])

export type CandidateFilter = {
  readonly itemId: string
  readonly text: string
  readonly resetLabel: string
  readonly onReset: () => void
}

export type CandidateListProps = {
  readonly title: string
  readonly aside: string
  readonly candidates: readonly CandidateView[]
  readonly items: readonly ItemView[]
  readonly selectedId: string
  readonly chosen: readonly string[]
  readonly filter?: CandidateFilter
  readonly noMatch: string
  readonly toolbar?: ReactNode
  readonly footer?: ReactNode
  readonly reveal?: boolean
  readonly onSelect: (id: string) => void
}

function targetIndex(key: string, index: number, last: number): number | null {
  if (NEXT_KEYS.has(key)) return Math.min(index + 1, last)
  if (PREV_KEYS.has(key)) return Math.max(index - 1, 0)
  if (key === "Home") return 0
  if (key === "End") return last
  return null
}

export function CandidateList({
  title,
  aside,
  candidates,
  items,
  selectedId,
  chosen,
  filter,
  noMatch,
  toolbar,
  footer,
  reveal = false,
  onSelect,
}: CandidateListProps) {
  const { t } = useTranslation("candidate")
  const listRef = useRef<HTMLDivElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [entering, setEntering] = useState(reveal)
  const hidden = candidates.length - VISIBLE_CANDIDATES
  const visible = expanded || hidden <= 0 ? candidates : candidates.slice(0, VISIBLE_CANDIDATES)
  const selectedVisible = visible.some((candidate) => candidate.id === selectedId)
  const lastReveal = Math.min(visible.length, REVEAL_LIMIT) - 1

  function move(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.altKey || event.ctrlKey || event.metaKey) return
    const next = targetIndex(event.key, index, visible.length - 1)
    const target = next === null ? undefined : visible[next]
    if (!target || next === null) return
    event.preventDefault()
    onSelect(target.id)
    listRef.current?.querySelectorAll<HTMLButtonElement>("[aria-pressed]")[next]?.focus()
  }

  function settle(event: AnimationEvent<HTMLDivElement>) {
    if (event.animationName !== REVEAL_ANIMATION) return
    const wrapper = (event.target as HTMLElement).closest<HTMLElement>("[data-reveal-index]")
    if (wrapper?.dataset.revealIndex === String(lastReveal)) setEntering(false)
  }

  return (
    <ResultSection title={title} aside={aside}>
      {toolbar}
      {filter ? (
        <div className={styles.note}>
          <div className={styles.clip}>
            <FilterNote
              text={filter.text}
              resetLabel={filter.resetLabel}
              onReset={filter.onReset}
            />
          </div>
        </div>
      ) : null}
      {candidates.length === 0 ? <Caption>{noMatch}</Caption> : null}
      <div ref={listRef} className={styles.list} onAnimationEnd={entering ? settle : undefined}>
        {visible.map((candidate, index) => {
          const selected = candidate.id === selectedId
          const revealIndex = entering && index <= lastReveal ? index : undefined
          return (
            <div key={candidate.id} data-reveal-index={revealIndex}>
              <CandidateCard
                candidate={candidate}
                items={items}
                selected={selected}
                chosen={chosen.includes(candidate.id)}
                focus={filter ? matchFor(candidate, filter.itemId) : undefined}
                reveal={revealIndex}
                tabIndex={selected || (!selectedVisible && index === 0) ? 0 : -1}
                onSelect={() => onSelect(candidate.id)}
                onKeyDown={(event) => move(event, index)}
              />
            </div>
          )
        })}
      </div>
      {hidden > 0 ? (
        <TextButton aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? t("list.showLess") : t("list.showMore", { count: hidden })}
        </TextButton>
      ) : null}
      {footer}
    </ResultSection>
  )
}
