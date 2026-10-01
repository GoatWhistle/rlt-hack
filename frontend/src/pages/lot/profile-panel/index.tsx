import { useTranslation } from "react-i18next"
import type { Company, Product, Source } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { Stack } from "@/shared/ui/stack"
import { SourceLine } from "../evidence-panel/source-line"
import styles from "./styles.module.css"

export type ProfilePanelProps = {
  readonly open: boolean
  readonly company: Company
  readonly products: readonly Product[]
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
  return (
    <dl className={styles.facts}>
      {site ? (
        <>
          <dt>{t("profile.site")}</dt>
          <dd>
            <a href={site}>{site}</a>
          </dd>
        </>
      ) : null}
      {email ? (
        <>
          <dt>{t("profile.email")}</dt>
          <dd>
            <a href={`mailto:${email}`}>{email}</a>
          </dd>
        </>
      ) : null}
      {phone ? (
        <>
          <dt>{t("profile.phone")}</dt>
          <dd>
            <a href={`tel:${phone.replace(/[^\d+]/g, "")}`}>{phone}</a>
          </dd>
        </>
      ) : null}
    </dl>
  )
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
        <dl className={styles.facts}>
          <dt>{t("profile.inn")}</dt>
          <dd className={styles.code}>{company.inn}</dd>
          <dt>{t("profile.role")}</dt>
          <dd>{company.role}</dd>
          <dt>{t("profile.roleBasis")}</dt>
          <dd>
            {company.roleSource ? (
              <SourceLine source={company.roleSource} />
            ) : (
              t("profile.noRoleBasis")
            )}
          </dd>
        </dl>
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
      <section className={styles.section}>
        <h3 className={styles.heading}>{t("profile.history")}</h3>
        <p>
          {t("evidence.purchasesSummary", {
            count: company.similarPurchases,
            wins: company.wins,
          })}
        </p>
        <Caption>{t("evidence.purchasesNote")}</Caption>
      </section>
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

export function ProfilePanel({ open, company, products, onClose }: ProfilePanelProps) {
  return (
    <Dialog open={open} size="side" title={company.name} onClose={onClose}>
      <Profile company={company} products={products} />
    </Dialog>
  )
}
