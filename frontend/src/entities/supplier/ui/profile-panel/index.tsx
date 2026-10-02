import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useRegionText, useRoleLabel } from "@/entities/evidence/labels"
import { ContactList } from "@/entities/evidence/ui/contact-list"
import { type OfferEntry, OfferGridSkeleton } from "@/entities/evidence/ui/offer-grid"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { SupplierProfile } from "@/entities/supplier/model"
import { useSupplierProfile } from "@/entities/supplier/queries"
import { Dialog } from "@/shared/ui/dialog"
import { ErrorState } from "@/shared/ui/error-state"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { LoadingState } from "@/shared/ui/loading-state"
import { Reveal } from "@/shared/ui/reveal"
import { SheetSection } from "@/shared/ui/sheet-section"
import { Bone } from "@/shared/ui/skeleton"
import { ProfileOffers } from "../profile-offers"
import styles from "./styles.module.css"

type ProfileProps = {
  readonly profile: SupplierProfile
  readonly matched: readonly OfferEntry[]
}

function Profile({ profile, matched }: ProfileProps) {
  const { t } = useTranslation("supplier")
  const roleLabel = useRoleLabel()
  const regionText = useRegionText()
  const facts: Fact[] = [
    { key: "inn", term: t("inn"), value: profile.inn || "—", mono: true },
    ...(profile.kpps.length > 0
      ? [{ key: "kpp", term: t("kpp"), value: profile.kpps.join(", "), mono: true }]
      : []),
    ...(profile.region
      ? [{ key: "region", term: t("region"), value: regionText(profile.region) }]
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
      <ProfileOffers offers={profile.offers} matched={matched} />
    </div>
  )
}

export const SKELETON_SECTIONS = [
  { id: "requisites", rows: 5 },
  { id: "contacts", rows: 3 },
] as const

const SKELETON = SKELETON_SECTIONS.map(({ id, rows }) => ({
  id,
  lines: Array.from({ length: rows }, (_, row) => ({
    id: `${id}-${row}`,
    short: row % 2 === 1,
  })),
}))

function ProfileSkeleton({ label }: { readonly label: string }) {
  return (
    <LoadingState label={label}>
      <div className={styles.skeleton}>
        {SKELETON.map((section) => (
          <div key={section.id} className={styles.block}>
            <Bone className={styles.heading} />
            {section.lines.map((line) => (
              <Bone key={line.id} className={line.short ? styles.short : styles.wide} />
            ))}
          </div>
        ))}
        <div className={styles.block}>
          <Bone className={styles.heading} />
          <OfferGridSkeleton />
        </div>
      </div>
    </LoadingState>
  )
}

type ProfileBodyProps = {
  readonly supplierId: string
  readonly matched: readonly OfferEntry[]
}

function ProfileBody({ supplierId, matched }: ProfileBodyProps) {
  const { t } = useTranslation("supplier")
  const profile = useSupplierProfile(supplierId)
  const [late] = useState(profile.isPending)
  if (profile.isPending) return <ProfileSkeleton label={t("loading")} />
  if (profile.isError)
    return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />
  return (
    <Reveal active={late}>
      <Profile profile={profile.data} matched={matched} />
    </Reveal>
  )
}

export type SupplierProfilePanelProps = {
  readonly open: boolean
  readonly supplierId: string
  readonly name: string
  readonly matched?: readonly OfferEntry[]
  readonly onClose: () => void
}

export function SupplierProfilePanel({
  open,
  supplierId,
  name,
  matched = [],
  onClose,
}: SupplierProfilePanelProps) {
  return (
    <Dialog open={open} size="side" title={name} onClose={onClose}>
      <ProfileBody key={supplierId} supplierId={supplierId} matched={matched} />
    </Dialog>
  )
}
