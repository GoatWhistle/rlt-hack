import { useTranslation } from "react-i18next"
import { useInnText, useRegionText, useRoleLabel } from "@/entities/evidence/labels"
import type { CandidateView } from "@/entities/evidence/view"
import { type Fact, FactList } from "@/shared/ui/fact-list"
import { Fold } from "@/shared/ui/fold"
import { ContactList } from "../contact-list"
import { SourceLine } from "../source-line"
import styles from "./styles.module.css"

export function CompanyBlock({ candidate }: { readonly candidate: CandidateView }) {
  const { t } = useTranslation("candidate")
  const roleLabel = useRoleLabel()
  const regionText = useRegionText()
  const innText = useInnText()
  const facts: Fact[] = [
    {
      key: "inn",
      term: t("panel.inn"),
      value: candidate.inn || innText(candidate.inn),
      mono: Boolean(candidate.inn),
    },
    { key: "role", term: t("panel.role"), value: roleLabel(candidate.role) },
    {
      key: "basis",
      term: t("panel.roleBasis"),
      value: candidate.roleSource ? (
        <SourceLine source={candidate.roleSource} />
      ) : (
        <span className={styles.missing}>{t("panel.noRoleBasis")}</span>
      ),
    },
    ...(candidate.region
      ? [{ key: "region", term: t("panel.region"), value: regionText(candidate.region) }]
      : []),
  ]
  return (
    <Fold title={t("panel.companyTitle")}>
      <div className={styles.company}>
        <FactList facts={facts} />
        <ContactList contacts={candidate.contacts} />
      </div>
    </Fold>
  )
}
