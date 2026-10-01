import { useTranslation } from "react-i18next"
import type { Source } from "@/entities/evidence/model"
import { ContactList } from "@/entities/evidence/ui/contact-list"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { Company, Product } from "@/entities/recommendation/model"
import { Caption } from "@/shared/ui/caption"
import { Dialog } from "@/shared/ui/dialog"
import { FactList } from "@/shared/ui/fact-list"
import { SheetSection } from "@/shared/ui/sheet-section"
import { Stack } from "@/shared/ui/stack"
import { useRoleText } from "../status"
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

type ProfileProps = Pick<ProfilePanelProps, "company" | "products">

function Profile({ company, products }: ProfileProps) {
  const { t } = useTranslation("lot")
  const { t: label } = useTranslation("evidence")
  const roleText = useRoleText()
  const names = new Map(products.map((product) => [product.id, product.name]))
  const sources = sourcesOf(company)
  return (
    <div className={styles.profile}>
      <SheetSection title={t("profile.requisites")}>
        <FactList
          facts={[
            { key: "inn", term: t("profile.inn"), value: company.inn, mono: true },
            { key: "role", term: t("profile.role"), value: roleText(company) },
            {
              key: "basis",
              term: t("profile.roleBasis"),
              value: company.roleSource ? (
                <SourceLine source={company.roleSource} />
              ) : (
                t("profile.noRoleBasis")
              ),
            },
          ]}
        />
      </SheetSection>
      <SheetSection title={t("profile.contacts")}>
        <ContactList contacts={company.contacts} />
      </SheetSection>
      <SheetSection title={t("profile.products")}>
        <Stack as="ul" gap="tight">
          {company.matches.map((match) => (
            <li key={match.productId} className={styles.line}>
              <span>{names.get(match.productId) ?? match.productId}</span>
              <span className={styles.muted}>{label(`basis.${match.basis}`)}</span>
            </li>
          ))}
        </Stack>
      </SheetSection>
      <SheetSection title={t("profile.history")}>
        <p>
          {t("evidence.purchasesSummary", {
            count: company.similarPurchases,
            wins: company.wins,
          })}
        </p>
        <Caption>{t("evidence.purchasesNote")}</Caption>
      </SheetSection>
      <SheetSection title={t("profile.sources")}>
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
      </SheetSection>
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
