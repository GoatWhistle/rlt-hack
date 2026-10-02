import { useTranslation } from "react-i18next"
import { useFormatters } from "@/shared/i18n/formatters"
import {
  type CandidateOrigin,
  type CandidateStatus,
  type CheckReason,
  type CompanyRole,
  countMatches,
  type Highlight,
  type MatchBasis,
} from "./model"
import { isRegionCode } from "./regions"

export function useRoleLabel(): (role: CompanyRole) => string {
  const { t } = useTranslation("evidence")
  return (role) => t(`role.${role}`)
}

export function useOriginLabel(): (origin: CandidateOrigin) => string {
  const { t } = useTranslation("evidence")
  return (origin) => t(`origin.${origin}`)
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

export function useCompanyName(): (company: {
  readonly name: string
  readonly inn: string
}) => string {
  const { t } = useTranslation("evidence")
  return ({ name, inn }) => name.trim() || (inn ? t("unnamed", { inn }) : t("unnamedNoInn"))
}

export function useInnText(): (inn: string) => string {
  const { t } = useTranslation("evidence")
  return (inn) => (inn ? t("inn", { inn }) : t("noInn"))
}

export type MatchFigure = {
  readonly value: string
  readonly note?: string
}

export function useMatchFigure(): (
  matches: readonly { readonly basis: MatchBasis }[],
  total: number,
) => MatchFigure {
  const { t } = useTranslation("evidence")
  const { number } = useFormatters()
  return (matches, total) => {
    const { confirmed, assumed } = countMatches(matches)
    return {
      value: `${number(confirmed)}/${number(total)}`,
      note: assumed > 0 ? t("assumed", { count: assumed }) : undefined,
    }
  }
}

export function useRegionText(): (code: string) => string {
  const { t } = useTranslation("evidence")
  return (code) =>
    isRegionCode(code)
      ? t("region.named", { name: t(`regionName.${code}`), code })
      : t("region.code", { code })
}
