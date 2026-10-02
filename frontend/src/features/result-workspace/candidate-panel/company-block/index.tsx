import { useTranslation } from "react-i18next"
import { useRegionText, useRoleLabel } from "@/entities/evidence/labels"
import { ContactList } from "@/entities/evidence/ui/contact-list"
import { SourceLine } from "@/entities/evidence/ui/source-line"
import type { Candidate } from "@/entities/search/model"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { PanelBlock } from "@/shared/ui/panel-block"
import styles from "./styles.module.css"

export function CompanyBlock({ candidate }: { readonly candidate: Candidate }) {
  const { t } = useTranslation("search")
  const roleLabel = useRoleLabel()
  const regionText = useRegionText()
  const facts: Fact[] = [
    { key: "role", term: t("evidence.role"), value: roleLabel(candidate.role) },
    {
      key: "basis",
      term: t("evidence.roleBasis"),
      value: candidate.roleSource ? (
        <SourceLine source={candidate.roleSource} />
      ) : (
        <span className={styles.missing}>{t("evidence.noRoleBasis")}</span>
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
