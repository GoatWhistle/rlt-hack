import { useTranslation } from "react-i18next"
import { OfferEmpty, type OfferEntry, OfferGrid } from "@/entities/evidence/ui/offer-grid"
import type { Offer } from "@/entities/supplier/model"
import { SheetSection } from "@/shared/ui/sheet-section"

export const OTHER_LIMIT = 4

export type ProfileOffersProps = {
  readonly offers: readonly Offer[]
  readonly matched: readonly OfferEntry[]
}

export function ProfileOffers({ offers, matched: snapshot }: ProfileOffersProps) {
  const { t } = useTranslation("supplier")
  const { t: label } = useTranslation("evidence")
  const current = new Map(offers.map((offer) => [offer.id, offer]))
  const matched = snapshot.map((entry) => ({
    ...entry,
    offer: current.get(entry.offer.id) ?? entry.offer,
  }))
  const shown = new Set(matched.map((entry) => entry.offer.id))
  const others = offers.filter((offer) => !shown.has(offer.id)).map((offer) => ({ offer }))
  const empty = matched.length === 0 && others.length === 0
  return (
    <>
      {matched.length > 0 ? (
        <SheetSection title={t("forQuery")}>
          <OfferGrid entries={matched} label={t("forQuery")} ribbon />
        </SheetSection>
      ) : null}
      {others.length > 0 || empty ? (
        <SheetSection title={matched.length > 0 ? t("otherOffers") : t("offers")}>
          {empty ? (
            <OfferEmpty title={label("offer.empty")} hint={label("offer.emptyHint")} />
          ) : (
            <OfferGrid
              entries={others}
              label={matched.length > 0 ? t("otherOffers") : t("offers")}
              limit={OTHER_LIMIT}
            />
          )}
        </SheetSection>
      ) : null}
    </>
  )
}
