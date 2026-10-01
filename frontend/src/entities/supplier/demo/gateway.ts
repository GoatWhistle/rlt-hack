import { demoProfilePayload } from "@/entities/search/demo/catalog"
import { ApiError } from "@/shared/api/api-error"
import { currentLocale } from "@/shared/i18n/i18n"
import type { Locale } from "@/shared/i18n/locale"
import type { SupplierGateway } from "../gateway"
import { parseSupplierProfile } from "../parse"

export type DemoSupplierOptions = {
  readonly locale?: () => Locale
}

export function supplierNotFound(): ApiError {
  return new ApiError({ status: 404, code: "supplier_not_found" })
}

export function createDemoSupplierGateway(options: DemoSupplierOptions = {}): SupplierGateway {
  const locale = options.locale ?? currentLocale
  return {
    profile: async (supplierId) => {
      const payload = demoProfilePayload(supplierId, locale())
      if (payload === undefined) throw supplierNotFound()
      return parseSupplierProfile(payload)
    },
  }
}
