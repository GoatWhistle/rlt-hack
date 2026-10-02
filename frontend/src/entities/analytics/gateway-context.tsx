import { createContext, type ReactNode, useContext } from "react"
import { apiClient } from "@/shared/api/client"
import { type AnalyticsGateway, createHttpAnalyticsGateway } from "./gateway"

let defaultGateway: AnalyticsGateway | undefined

export function appAnalyticsGateway(): AnalyticsGateway {
  defaultGateway ??= createHttpAnalyticsGateway(apiClient)
  return defaultGateway
}

const GatewayContext = createContext<AnalyticsGateway | null>(null)

export type AnalyticsGatewayProviderProps = {
  readonly gateway: AnalyticsGateway
  readonly children: ReactNode
}

export function AnalyticsGatewayProvider({ gateway, children }: AnalyticsGatewayProviderProps) {
  return <GatewayContext.Provider value={gateway}>{children}</GatewayContext.Provider>
}

export function useAnalyticsGateway(): AnalyticsGateway {
  return useContext(GatewayContext) ?? appAnalyticsGateway()
}
