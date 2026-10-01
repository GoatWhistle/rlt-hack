import { useTranslation } from "react-i18next"
import type { CandidateStatus, CheckReason, CompanyRole, Highlight } from "./model"

export function useRoleLabel(): (role: CompanyRole) => string {
  const { t } = useTranslation("evidence")
  return (role) => t(`role.${role}`)
}

export function useStatusLabel(): (status: CandidateStatus) => string {
  const { t } = useTranslation("evidence")
  return (status) => t(`status.${status}`)
}

export function useHighlightText(): (highlight: Highlight) => string {
  const { t } = useTranslation("evidence")
  return ({ code, params }) => {
    if (code === "coversItems") {
      return t("highlight.coversItems", {
        matched: params.matched ?? 0,
        total: params.total ?? 0,
      })
    }
    if (code === "verifiedIdentity") return t("highlight.verifiedIdentity")
    return t(`highlight.${code}`, { count: params.count ?? 0 })
  }
}

export function useCheckReasonText(): (reason: CheckReason) => string {
  const { t } = useTranslation("evidence")
  return (reason) => t(`checkReason.${reason}`)
}

export function useInnText(): (inn: string) => string {
  const { t } = useTranslation("evidence")
  return (inn) => (inn ? t("inn", { inn }) : t("noInn"))
}
