import { createContext, type ReactNode, useContext } from "react"
import { apiClient } from "@/shared/api/client"
import { env } from "@/shared/config/env"
import { createDemoGateway } from "./demo/gateway"
import type { UploadGateway } from "./gateway"
import { createHttpGateway } from "./http"

let defaultGateway: UploadGateway | undefined

export function appGateway(): UploadGateway {
  defaultGateway ??= env.demoMode ? createDemoGateway() : createHttpGateway(apiClient)
  return defaultGateway
}

const GatewayContext = createContext<UploadGateway | null>(null)

export type UploadGatewayProviderProps = {
  readonly gateway: UploadGateway
  readonly children: ReactNode
}

export function UploadGatewayProvider({ gateway, children }: UploadGatewayProviderProps) {
  return <GatewayContext.Provider value={gateway}>{children}</GatewayContext.Provider>
}

export function useUploadGateway(): UploadGateway {
  return useContext(GatewayContext) ?? appGateway()
}
