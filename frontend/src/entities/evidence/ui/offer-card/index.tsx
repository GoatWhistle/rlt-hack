import { clsx } from "clsx"
import { useId } from "react"
import { useTranslation } from "react-i18next"
import {
  type Availability,
  isStale,
  type MatchBasis,
  type OfferView,
} from "@/entities/evidence/model"
import { useOfferText } from "@/entities/evidence/offer-labels"
import { Dot } from "@/shared/ui/dot"
import { FactRow } from "@/shared/ui/fact-row"
import { Icon, type IconName } from "@/shared/ui/icon"
import { Tag, type TagTone } from "@/shared/ui/tag"
import { VisuallyHidden } from "@/shared/ui/visually-hidden"
import { BasisMarker } from "../match-row"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

const AVAILABILITY: Record<Availability, { readonly tone: TagTone; readonly icon?: IconName }> =
  {
    available: { tone: "success", icon: "check" },
    on_order: { tone: "solid", icon: "clock" },
    unavailable: { tone: "solid", icon: "close" },
    unknown: { tone: "tentative" },
  }

const BASIS_TEXT: Record<MatchBasis, string | undefined> = {
  stock: styles.stock,
  catalog: styles.catalog,
  inferred: styles.inferred,
}

export type OfferLink = {
  readonly itemName: string
  readonly basis: MatchBasis
}

export type OfferCardProps = {
  readonly offer: OfferView
  readonly link?: OfferLink
  readonly focused?: boolean
}

function OfferName({ offer, id }: { readonly offer: OfferView; readonly id: string }) {
  const { t } = useTranslation("evidence")
  const url = offer.source?.url
  return (
    <p id={id} className={styles.name}>
      {url ? (
        <a href={url} target="_blank" rel="noopener noreferrer" className={styles.link}>
          {offer.name}
          <VisuallyHidden> {t("newTab")}</VisuallyHidden>
        </a>
      ) : (
        offer.name
      )}
    </p>
  )
}

function OfferFacts({ offer }: { readonly offer: OfferView }) {
  const { t } = useTranslation("evidence")
  const facts = [
    offer.brand ? { key: "brand", text: offer.brand, code: false } : null,
    offer.article
      ? { key: "article", text: t("offer.article", { article: offer.article }), code: true }
      : null,
    offer.okpd2
      ? { key: "okpd2", text: t("offer.okpd2", { code: offer.okpd2 }), code: true }
      : null,
  ].filter((fact) => fact !== null)
  const attributes = offer.attributes ?? []
  return (
    <>
      {facts.length > 0 ? (
        <p className={styles.facts}>
          <FactRow>
            {facts.map((fact) => (
              <span key={fact.key} className={fact.code ? styles.code : undefined}>
                {fact.text}
              </span>
            ))}
          </FactRow>
        </p>
      ) : null}
      {attributes.length > 0 ? (
        <p className={styles.facts}>
          <FactRow>
            {attributes.map((entry) => (
              <span key={entry.name}>
                {t("offer.attribute", { name: entry.name, value: entry.value })}
              </span>
            ))}
          </FactRow>
        </p>
      ) : null}
    </>
  )
}

export function OfferCard({ offer, link, focused = false }: OfferCardProps) {
  const { t } = useTranslation("evidence")
  const text = useOfferText()
  const nameId = useId()
  const availability = offer.availability ?? "unknown"
  const look = AVAILABILITY[availability]
  const seller = offer.seller && offer.seller !== "verified" ? offer.seller : undefined
  return (
    <article
      className={styles.card}
      aria-labelledby={nameId}
      aria-current={focused || undefined}
    >
      <div className={styles.head}>
        {offer.imageUrl ? (
          <img
            className={styles.image}
            src={offer.imageUrl}
            alt=""
            loading="lazy"
            decoding="async"
          />
        ) : null}
        <div className={styles.main}>
          <OfferName offer={offer} id={nameId} />
          <OfferFacts offer={offer} />
        </div>
      </div>
      {offer.price !== undefined || offer.availability ? (
        <div className={styles.deal}>
          <span className={clsx(styles.price, offer.price === undefined && styles.noPrice)}>
            {text.price(offer)}
          </span>
          <Tag tone={look.tone}>
            {look.icon ? <Icon name={look.icon} size="sm" /> : null}
            {text.availability(availability)}
          </Tag>
        </div>
      ) : null}
      {seller ? (
        <p className={styles.seller}>
          <Dot shape="dashed" tone="warning" />
          {t(`offer.seller.${seller}`)}
        </p>
      ) : null}
      <div className={styles.foot}>
        {link ? (
          <p className={styles.relation}>
            <BasisMarker basis={link.basis} />
            <span className={styles.relationText}>
              <FactRow>
                <span>{t("offer.item", { name: link.itemName })}</span>
                <span className={clsx(styles.basis, BASIS_TEXT[link.basis])}>
                  {t(`basis.${link.basis}`)}
                </span>
              </FactRow>
            </span>
          </p>
        ) : null}
        <SourceLine source={offer.source} stale={isStale(offer.source?.checkedAt)} />
      </div>
    </article>
  )
}
