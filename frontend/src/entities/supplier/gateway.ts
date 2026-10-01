import type { HttpClient } from "@/shared/api/http-client"
import type { SupplierProfile } from "./model"
import { parseSupplierProfile } from "./parse"

export const SUPPLIERS_PATH = "/suppliers"

export type SupplierGateway = {
  readonly profile: (supplierId: string) => Promise<SupplierProfile>
}

export function createHttpSupplierGateway(client: HttpClient): SupplierGateway {
  return {
    profile: (supplierId) =>
      client.get(`${SUPPLIERS_PATH}/${encodeURIComponent(supplierId)}`, {
        parse: parseSupplierProfile,
      }),
  }
}
