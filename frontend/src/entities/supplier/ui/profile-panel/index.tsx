import { useTranslation } from "react-i18next"
import { useRoleLabel } from "@/entities/evidence/labels"
import { ContactList } from "@/entities/evidence/ui/contact-list"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { SupplierProfile } from "@/entities/supplier/model"
import { useSupplierProfile } from "@/entities/supplier/queries"
import { Dialog } from "@/shared/ui/dialog"
import { ErrorState } from "@/shared/ui/error-state"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { LoadingState } from "@/shared/ui/loading-state"
import { SheetSection } from "@/shared/ui/sheet-section"
import { OfferList } from "../offer-list"
import styles from "./styles.module.css"

function Profile({ profile }: { readonly profile: SupplierProfile }) {
  const { t } = useTranslation("supplier")
  const roleLabel = useRoleLabel()
  const facts: Fact[] = [
    { key: "inn", term: t("inn"), value: profile.inn || "—", mono: true },
    ...(profile.kpps.length > 0
      ? [{ key: "kpp", term: t("kpp"), value: profile.kpps.join(", "), mono: true }]
      : []),
    ...(profile.region
      ? [{ key: "region", term: t("region"), value: profile.region, mono: true }]
      : []),
    { key: "identity", term: t("identity.title"), value: t(`identity.${profile.identity}`) },
    { key: "role", term: t("role"), value: roleLabel(profile.role) },
    {
      key: "basis",
      term: t("roleBasis"),
      value: profile.roleSource ? <SourceLine source={profile.roleSource} /> : t("noRoleBasis"),
    },
  ]
  return (
    <div className={styles.profile}>
      <SheetSection title={t("requisites")}>
        <FactList facts={facts} />
      </SheetSection>
      <SheetSection title={t("contacts")}>
        <ContactList contacts={profile.contacts} />
      </SheetSection>
      <SheetSection title={t("offers")}>
        <OfferList offers={profile.offers} />
      </SheetSection>
    </div>
  )
}

function ProfileBody({ supplierId }: { readonly supplierId: string }) {
  const { t } = useTranslation("supplier")
  const profile = useSupplierProfile(supplierId)
  if (profile.isPending) return <LoadingState label={t("loading")} />
  if (profile.isError)
    return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />
  return <Profile profile={profile.data} />
}

export type SupplierProfilePanelProps = {
  readonly open: boolean
  readonly supplierId: string
  readonly name: string
  readonly onClose: () => void
}

export function SupplierProfilePanel({
  open,
  supplierId,
  name,
  onClose,
}: SupplierProfilePanelProps) {
  return (
    <Dialog open={open} size="side" title={name} onClose={onClose}>
      {open ? <ProfileBody supplierId={supplierId} /> : null}
    </Dialog>
  )
}
