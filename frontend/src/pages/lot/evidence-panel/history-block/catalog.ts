import type { OfferView } from "@/entities/evidence/model"
import type { CatalogOffer } from "@/entities/recommendation/model"

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}

export function catalogOfferView(item: CatalogOffer): OfferView {
  const checked = Number.isFinite(Date.parse(item.checkedAt)) ? item.checkedAt : undefined
  return {
    id: item.url,
    name: item.name,
    source: {
      kind: "catalog",
      title: hostOf(item.url),
      url: item.url,
      ...(checked ? { checkedAt: checked } : {}),
    },
  }
}
