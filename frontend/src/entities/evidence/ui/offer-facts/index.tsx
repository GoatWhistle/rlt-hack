import { clsx } from "clsx"
import { useTranslation } from "react-i18next"
import type { OfferSnapshot, RequirementCheck } from "@/entities/evidence/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { Icon, type IconName } from "@/shared/ui/icon"
import styles from "./styles.module.css"

const MARKS: Record<RequirementCheck["status"], IconName> = {
  met: "check",
  conflict: "close",
  unknown: "minus",
}

const LOOKS: Record<RequirementCheck["status"], string | undefined> = {
  met: styles.met,
  conflict: styles.conflict,
  unknown: styles.unknown,
}

const REGISTERED = new Set(["registry", "dataset"])

export type OfferFactsProps = {
  readonly offer?: OfferSnapshot
  readonly checks: readonly RequirementCheck[]
}

export function OfferFacts({ offer, checks }: OfferFactsProps) {
  const { t } = useTranslation("evidence")
  const { money } = useFormatters()
  if (!offer && checks.length === 0) return null
  const price =
    offer?.price && Number.isFinite(Number(offer.price))
      ? money(Number(offer.price), offer.currency || "RUB")
      : undefined
  const facts = offer
    ? [t(`link.${offer.link}`), t(`availability.${offer.availability}`), price]
    : []
  return (
    <div className={styles.facts}>
      {offer ? <span className={styles.offer}>{offer.name}</span> : null}
      {facts.length > 0 ? (
        <span className={styles.line}>{facts.filter(Boolean).join(" · ")}</span>
      ) : null}
      {offer && REGISTERED.has(offer.sourceType) ? (
        <span className={styles.note}>{t("registeredNote")}</span>
      ) : null}
      {checks.length > 0 ? (
        <ul className={styles.checks} aria-label={t("checksLabel")}>
          {checks.map((check) => (
            <li
              key={check.key + check.value}
              className={clsx(styles.check, LOOKS[check.status])}
            >
              <Icon name={MARKS[check.status]} size="sm" />
              {t(`check.${check.status}`, { text: check.text, found: check.found ?? "" })}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
