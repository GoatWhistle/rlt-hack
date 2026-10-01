import { createContext, type ReactNode, useContext } from "react"
import { apiClient } from "@/shared/api/client"
import type { SearchGateway } from "./gateway"
import { createHttpSearchGateway } from "./http"

let defaultGateway: SearchGateway | undefined

export function appSearchGateway(): SearchGateway {
  defaultGateway ??= createHttpSearchGateway(apiClient)
  return defaultGateway
}

const GatewayContext = createContext<SearchGateway | null>(null)

export type SearchGatewayProviderProps = {
  readonly gateway: SearchGateway
  readonly children: ReactNode
}

export function SearchGatewayProvider({ gateway, children }: SearchGatewayProviderProps) {
  return <GatewayContext.Provider value={gateway}>{children}</GatewayContext.Provider>
}

export function useSearchGateway(): SearchGateway {
  return useContext(GatewayContext) ?? appSearchGateway()
}
