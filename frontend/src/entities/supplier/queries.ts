import { useQuery } from "@tanstack/react-query"
import { keptAcrossLocales } from "@/shared/api/locale-keys"
import type { Locale } from "@/shared/i18n/locale"
import { useLocale } from "@/shared/i18n/locale-provider"
import { useSupplierGateway } from "./gateway-context"

export const supplierKeys = {
  profile: (locale: Locale, supplierId: string) =>
    ["suppliers", locale, "profile", supplierId] as const,
}

export function useSupplierProfile(supplierId: string, enabled = true) {
  const gateway = useSupplierGateway()
  const { locale } = useLocale()
  const key = supplierKeys.profile(locale, supplierId)
  return useQuery({
    queryKey: key,
    queryFn: () => gateway.profile(supplierId),
    placeholderData: keptAcrossLocales(key),
    enabled,
  })
}
