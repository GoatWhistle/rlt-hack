import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/shared/api/client"
import {
  list,
  oneOf,
  optionalText,
  PayloadFormatError,
  plainText,
  record,
  text,
} from "@/shared/api/payload"

const OUTCOMES = ["winner", "participant"] as const

export type PurchaseSource = {
  readonly title: string
  readonly lotId: string
  readonly supplierInn: string
  readonly customerInn?: string
  readonly category: string
  readonly system: string
  readonly products: readonly string[]
  readonly winner: boolean
  readonly date: string
  readonly snapshot: string
}

export function parsePurchaseSource(value: unknown): PurchaseSource {
  const fields = record(value, "$")
  oneOf(["procurementArchive"], fields, "provenance", "$")
  const date = text(fields, "publishedAt", "$")
  if (!Number.isFinite(Date.parse(date))) throw new PayloadFormatError("$.publishedAt")
  const customerInn = optionalText(fields, "customerInn", "$")
  return {
    title: text(fields, "title", "$"),
    lotId: text(fields, "lotId", "$"),
    supplierInn: text(fields, "supplierInn", "$"),
    ...(customerInn ? { customerInn } : {}),
    category: plainText(fields.category, "$.category"),
    system: plainText(fields.sourceSystem, "$.sourceSystem"),
    products: list(fields, "products", "$", plainText),
    winner: oneOf(OUTCOMES, fields, "outcome", "$") === "winner",
    date,
    snapshot: plainText(fields.snapshot, "$.snapshot"),
  }
}

export function usePurchaseSource(supplierId: string, lotId: string) {
  return useQuery({
    queryKey: ["purchase-source", supplierId, lotId],
    queryFn: ({ signal }) =>
      apiClient.get(
        `/suppliers/${encodeURIComponent(supplierId)}/purchases/${encodeURIComponent(lotId)}`,
        { signal, parse: parsePurchaseSource },
      ),
  })
}
