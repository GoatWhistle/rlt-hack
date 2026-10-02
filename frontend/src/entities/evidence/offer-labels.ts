import { useTranslation } from "react-i18next"
import { useFormatters } from "@/shared/i18n/formatters"
import type { Availability, OfferView } from "./model"

const CURRENCY_CODE = /^[a-z]{3}$/i

export type OfferText = {
  readonly price: (offer: OfferView) => string
  readonly availability: (value: Availability) => string
  readonly short: (offer: OfferView) => string
}

export function useOfferText(): OfferText {
  const { t } = useTranslation("evidence")
  const { money, number } = useFormatters()
  const amount = (offer: OfferView, value: number) => {
    if (!offer.currency) return number(value)
    if (CURRENCY_CODE.test(offer.currency)) return money(value, offer.currency.toUpperCase())
    return t("offer.amount", { value: number(value), currency: offer.currency })
  }
  const price = (offer: OfferView) => {
    if (offer.price === undefined) return t("offer.noPrice")
    const value = amount(offer, offer.price)
    return offer.unit ? t("offer.price", { price: value, unit: offer.unit }) : value
  }
  const availability = (value: Availability) => t(`offer.availability.${value}`)
  const short = (offer: OfferView) =>
    t("offer.short", {
      price: price(offer),
      availability: availability(offer.availability ?? "unknown"),
    })
  return { price, availability, short }
}
