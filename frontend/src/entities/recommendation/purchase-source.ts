import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/shared/api/client"
import { list, oneOf, PayloadFormatError, plainText, record, text } from "@/shared/api/payload"

export function parsePurchaseSource(value: unknown) {
  const fields = record(value, "$")
  oneOf(["procurement_archive"], fields, "provenance", "$")
  if (typeof fields.is_winner !== "boolean") throw new PayloadFormatError("$.is_winner")
  const date = text(fields, "publish_date", "$")
  if (!Number.isFinite(Date.parse(date))) throw new PayloadFormatError("$.publish_date")
  return {
    title: text(fields, "title", "$"),
    lotId: text(fields, "lot_id", "$"),
    supplierInn: text(fields, "supplier_inn", "$"),
    customerInn: text(fields, "customer_inn", "$"),
    category: text(fields, "category", "$"),
    system: text(fields, "source_system", "$"),
    products: list(fields, "product_names", "$", plainText),
    winner: fields.is_winner,
    date,
  }
}

export function usePurchaseSource(upload: string, lot: string, inn: string, purchase: string) {
  return useQuery({
    queryKey: ["purchase-source", upload, lot, inn, purchase],
    queryFn: ({ signal }) =>
      apiClient.get(
        `/uploads/${encodeURIComponent(upload)}/lots/${encodeURIComponent(lot)}/evidence/${encodeURIComponent(inn)}/${encodeURIComponent(purchase)}`,
        { signal, parse: parsePurchaseSource },
      ),
  })
}
