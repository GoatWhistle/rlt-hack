import { useMutation } from "@tanstack/react-query"
import { apiClient } from "@/shared/api/client"
import type { HttpClient } from "@/shared/api/http-client"
import { env } from "@/shared/config/env"
import demoResult from "./demo-result.json"
import type { Recommendation } from "./model"
import { parseRecommendation } from "./parse"

export const RECOMMENDATIONS_PATH = "/recommendations"
export const DEMO_DELAY_MS = 400

export type RecommendationSource = {
  readonly client: HttpClient
  readonly demoMode: boolean
}

const defaultSource: RecommendationSource = { client: apiClient, demoMode: env.demoMode }

export async function requestRecommendation(
  file: File,
  source: RecommendationSource = defaultSource,
): Promise<Recommendation> {
  if (source.demoMode) {
    await new Promise((resolve) => setTimeout(resolve, DEMO_DELAY_MS))
    return parseRecommendation({ ...demoResult, fileName: file.name })
  }
  const body = new FormData()
  body.append("file", file)
  return source.client.post(RECOMMENDATIONS_PATH, { body, parse: parseRecommendation })
}

export function useRecommendationRequest(source?: RecommendationSource) {
  return useMutation({ mutationFn: (file: File) => requestRecommendation(file, source) })
}
