import { useTranslation } from "react-i18next"
import { useOriginLabel, useRegionText, useRoleLabel } from "@/entities/evidence/labels"
import { ContactList } from "@/entities/evidence/ui/contact-list"
import { RoleBasisNote } from "@/entities/evidence/ui/role-basis"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { Candidate } from "@/entities/search/model"
import { useFormatters } from "@/shared/i18n/formatters"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { PanelBlock } from "@/shared/ui/panel-block"
import styles from "./styles.module.css"

export type CompanyBlockProps = {
  readonly candidate: Candidate
  readonly noveltySet?: string
}

export function CompanyBlock({ candidate, noveltySet }: CompanyBlockProps) {
  const { t } = useTranslation("search")
  const roleLabel = useRoleLabel()
  const regionText = useRegionText()
  const originLabel = useOriginLabel()
  const { list } = useFormatters()
  const set = noveltySet ?? ""
  const novelty = {
    new: t("evidence.noveltyNew", { set }),
    known: t("evidence.noveltyKnown", { set }),
    unknown: t("evidence.noveltyUnknown"),
  }[candidate.novelty]
  const facts: Fact[] = [
    { key: "novelty", term: t("evidence.novelty"), value: novelty },
    {
      key: "origins",
      term: t("evidence.foundBy"),
      value:
        candidate.origins.length > 0
          ? list(candidate.origins.map(originLabel))
          : t("evidence.noOrigin"),
    },
    { key: "role", term: t("evidence.role"), value: roleLabel(candidate.role) },
    {
      key: "basis",
      term: t("evidence.roleBasis"),
      value: (
        <>
          {candidate.roleSource ? (
            <SourceLine source={candidate.roleSource} />
          ) : (
            <span className={styles.missing}>{t("evidence.noRoleBasis")}</span>
          )}
          <RoleBasisNote context={candidate.roleContext} />
        </>
      ),
    },
    ...(candidate.region
      ? [{ key: "region", term: t("evidence.region"), value: regionText(candidate.region) }]
      : []),
  ]
  return (
    <PanelBlock title={t("evidence.companyTitle")}>
      <div className={styles.company}>
        <FactList facts={facts} />
        <ContactList contacts={candidate.contacts} />
      </div>
    </PanelBlock>
  )
}
