import { useTranslation } from "react-i18next"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { Company, Product, Source } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { type Choice, ChoiceButton } from "@/shared/ui/choice-button"
import { Dialog } from "@/shared/ui/dialog"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { Stack } from "@/shared/ui/stack"
import { HistoryBlock } from "../evidence-panel/history-block"
import styles from "./styles.module.css"

export type ProfilePanelProps = {
  readonly open: boolean
  readonly company: Company
  readonly products: readonly Product[]
  readonly choice?: Choice
  readonly onClose: () => void
}

function sourcesOf(company: Company): Source[] {
  const all = [
    company.roleSource,
    ...company.matches.map((match) => match.source),
    ...company.purchases.map((purchase) => purchase.source),
  ].filter((source): source is Source => source !== undefined)
  const seen = new Set<string>()
  return all.filter((source) => {
    const key = `${source.kind}:${source.title}:${source.url}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function Contacts({ company }: { readonly company: Company }) {
  const { t } = useTranslation("lot")
  const { site, email, phone } = company.contacts ?? {}
  if (!site && !email && !phone) return <Caption>{t("profile.noContacts")}</Caption>
  const facts: Fact[] = [
    ...(site
      ? [{ key: "site", term: t("profile.site"), value: <a href={site}>{site}</a> }]
      : []),
    ...(email
      ? [
          {
            key: "email",
            term: t("profile.email"),
            value: <a href={`mailto:${email}`}>{email}</a>,
          },
        ]
      : []),
    ...(phone
      ? [
          {
            key: "phone",
            term: t("profile.phone"),
            value: <a href={`tel:${phone.replace(/[^\d+]/g, "")}`}>{phone}</a>,
          },
        ]
      : []),
  ]
  return <FactList facts={facts} />
}

type ProfileProps = Pick<ProfilePanelProps, "company" | "products">

function Profile({ company, products }: ProfileProps) {
  const { t } = useTranslation("lot")
  const names = new Map(products.map((product) => [product.id, product.name]))
  const sources = sourcesOf(company)
  return (
    <div className={styles.profile}>
      <section className={styles.section}>
        <h3 className={styles.heading}>{t("profile.requisites")}</h3>
        <FactList
          facts={[
            { key: "inn", term: t("profile.inn"), value: company.inn, mono: true },
            ...(company.identitySource
              ? [
                  {
                    key: "identity",
                    term: t("history.companySource"),
                    value: <a href={company.identitySource}>{t("history.openSource")}</a>,
                  },
                ]
              : []),
            { key: "role", term: t("profile.role"), value: company.role },
            {
              key: "roleBasis",
              term: t("profile.roleBasis"),
              value: company.roleSource ? (
                <SourceLine source={company.roleSource} />
              ) : (
                t("profile.noRoleBasis")
              ),
            },
          ]}
        />
      </section>
      <section className={styles.section}>
        <h3 className={styles.heading}>{t("profile.contacts")}</h3>
        <Contacts company={company} />
      </section>
      <section className={styles.section}>
        <h3 className={styles.heading}>{t("profile.products")}</h3>
        <Stack as="ul" gap="tight">
          {company.matches.map((match) => (
            <li key={match.productId} className={styles.line}>
              <span>{names.get(match.productId) ?? match.productId}</span>
              <span className={styles.muted}>{t(`evidence.basis.${match.basis}`)}</span>
            </li>
          ))}
        </Stack>
      </section>
      {company.history ? (
        <HistoryBlock company={company} />
      ) : (
        <section className={styles.section}>
          <h3 className={styles.heading}>{t("profile.history")}</h3>
          <p>
            {company.similarPurchases === null || company.wins === null
              ? t("compare.unknown")
              : t("evidence.purchasesSummary", {
                  count: company.similarPurchases,
                  wins: company.wins,
                })}
          </p>
          <Caption>{t("evidence.purchasesNote")}</Caption>
        </section>
      )}
      <section className={styles.section}>
        <h3 className={styles.heading}>{t("profile.sources")}</h3>
        {sources.length > 0 ? (
          <Stack as="ul" gap="tight">
            {sources.map((source) => (
              <li key={`${source.kind}:${source.title}:${source.url}`}>
                <SourceLine source={source} />
              </li>
            ))}
          </Stack>
        ) : (
          <Caption>{t("profile.noSources")}</Caption>
        )}
      </section>
    </div>
  )
}

export function ProfilePanel({ open, company, products, choice, onClose }: ProfilePanelProps) {
  const { t } = useTranslation("lot")
  return (
    <Dialog
      open={open}
      size="side"
      title={company.name}
      onClose={onClose}
      footer={
        choice ? (
          <ChoiceButton
            {...choice}
            chooseLabel={t("evidence.choose")}
            chosenLabel={t("evidence.chosen")}
          />
        ) : null
      }
    >
      <Profile company={company} products={products} />
    </Dialog>
  )
}
