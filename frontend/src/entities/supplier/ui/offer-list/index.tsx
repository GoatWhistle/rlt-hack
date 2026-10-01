import { useTranslation } from "react-i18next"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { Availability, Offer } from "@/entities/supplier/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Caption } from "@/shared/ui/caption"
import { Tag, type TagTone } from "@/shared/ui/tag"
import styles from "./styles.module.css"

const AVAILABILITY_TONES: Record<Availability, TagTone> = {
  available: "success",
  on_order: "solid",
  unavailable: "warning",
  unknown: "tentative",
}

function OfferRow({ offer }: { readonly offer: Offer }) {
  const { t } = useTranslation("supplier")
  const { money } = useFormatters()
  return (
    <div className={styles.offer}>
      <div className={styles.head}>
        <span className={styles.name}>{offer.name}</span>
        <Tag tone={AVAILABILITY_TONES[offer.availability]}>
          {t(`availability.${offer.availability}`)}
        </Tag>
      </div>
      <span className={styles.price}>
        {offer.price === undefined
          ? t("noPrice")
          : t("price", { price: money(offer.price, offer.currency), unit: offer.unit })}
      </span>
      <SourceLine source={offer.source} />
    </div>
  )
}

export function OfferList({ offers }: { readonly offers: readonly Offer[] }) {
  const { t } = useTranslation("supplier")
  if (offers.length === 0) return <Caption>{t("noOffers")}</Caption>
  return (
    <ul className={styles.list}>
      {offers.map((offer) => (
        <li key={offer.id}>
          <OfferRow offer={offer} />
        </li>
      ))}
    </ul>
  )
}
