import { useTranslation } from "react-i18next"
import type { OfferView } from "@/entities/evidence/model"
import { useOfferText } from "@/entities/evidence/offer-labels"
import { type CandidateView, type ItemView, matchFor } from "@/entities/evidence/view"
import { type CompareCriterion, ValueLines } from "./compare-table"

type Holder = { readonly candidate: CandidateView }

function offerFor(candidate: CandidateView, itemId: string): OfferView | undefined {
  return matchFor(candidate, itemId)?.offer
}

export function comparablePrices(
  candidates: readonly CandidateView[],
  itemId: string,
): ReadonlyMap<string, number> {
  const priced = candidates.flatMap((candidate) => {
    const offer = offerFor(candidate, itemId)
    return offer?.price !== undefined && offer.price > 0 ? [{ id: candidate.id, offer }] : []
  })
  const units = new Set(
    priced.map(({ offer }) => `${offer.currency ?? ""}/${offer.unit ?? ""}`),
  )
  if (priced.length < 2 || units.size !== 1) return new Map()
  return new Map(priced.map(({ id, offer }) => [id, offer.price ?? 0]))
}

export function useOfferCriteria<T extends Holder>(
  items: readonly ItemView[],
  candidates: readonly CandidateView[],
): CompareCriterion<T>[] {
  const { t } = useTranslation("evidence")
  const text = useOfferText()
  return items
    .filter((item) => candidates.some((candidate) => offerFor(candidate, item.id)))
    .map((item) => {
      const prices = comparablePrices(candidates, item.id)
      return {
        id: `offer-${item.id}`,
        label: item.name,
        value: ({ candidate }: T) => {
          const match = matchFor(candidate, item.id)
          if (match?.offer) {
            return (
              <ValueLines
                lines={[text.price(match.offer)]}
                detail={text.availability(match.offer.availability ?? "unknown")}
              />
            )
          }
          return match ? t(`basis.${match.basis}`) : t("notFound")
        },
        score:
          prices.size > 0
            ? ({ candidate }: T) => {
                const price = prices.get(candidate.id)
                return price === undefined ? 0 : 1 / price
              }
            : undefined,
      }
    })
}
