import type { Notice } from "@/entities/notice/model"
import { demoPayload } from "@/entities/recommendation/demo"
import type { Recommendation } from "@/entities/recommendation/model"
import { parseRecommendation } from "@/entities/recommendation/parse"

const VARIANTS = 10
const EMPTY_VARIANT = 0
const LAST_ASSUMED_VARIANT = 4

let template: Recommendation | undefined

function base(): Recommendation {
  template ??= parseRecommendation({ ...demoPayload, fileName: "" })
  return template
}

export function variantOf(lotId: string): number {
  let hash = 0
  for (const char of lotId) hash = (hash * 31 + (char.codePointAt(0) ?? 0)) % 1_000_003
  return hash % VARIANTS
}

function withoutAssumptions(recommendation: Recommendation): Recommendation {
  const products = recommendation.products.filter((product) => product.origin !== "inferred")
  const kept = new Set(products.map((product) => product.id))
  const companies = recommendation.companies
    .map((company) => ({
      ...company,
      matches: company.matches.filter((match) => kept.has(match.productId)),
    }))
    .filter((company) => company.matches.length > 0)
  return { ...recommendation, products, companies }
}

export function demoRecommendation(notice: Notice, fileName: string): Recommendation {
  const variant = variantOf(notice.lotId)
  const source = base()
  const shaped =
    variant === EMPTY_VARIANT
      ? { ...source, companies: [] }
      : variant <= LAST_ASSUMED_VARIANT
        ? source
        : withoutAssumptions(source)
  return { ...shaped, fileName, requestTitle: notice.title, lotLabel: notice.lotId }
}
