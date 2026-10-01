import { createContext, type ReactNode, useContext } from "react"
import { apiClient } from "@/shared/api/client"
import { env } from "@/shared/config/env"
import { createDemoSupplierGateway } from "./demo/gateway"
import { createHttpSupplierGateway, type SupplierGateway } from "./gateway"

let defaultGateway: SupplierGateway | undefined

export function appSupplierGateway(): SupplierGateway {
  defaultGateway ??= env.demoMode
    ? createDemoSupplierGateway()
    : createHttpSupplierGateway(apiClient)
  return defaultGateway
}

const GatewayContext = createContext<SupplierGateway | null>(null)

export type SupplierGatewayProviderProps = {
  readonly gateway: SupplierGateway
  readonly children: ReactNode
}

export function SupplierGatewayProvider({ gateway, children }: SupplierGatewayProviderProps) {
  return <GatewayContext.Provider value={gateway}>{children}</GatewayContext.Provider>
}

export function useSupplierGateway(): SupplierGateway {
  return useContext(GatewayContext) ?? appSupplierGateway()
}
