import { apiClient } from "./client"

export type DocumentExtraction = {
  id: string
  workspace_id: string
  document_knowledge: Record<string, unknown>
  created_at: string
  updated_at: string
}

export async function extractDocuments(
  workspaceId: string,
  timeoutMs?: number,
): Promise<DocumentExtraction> {
  const response = await apiClient.post<DocumentExtraction>(
    `/workspaces/${workspaceId}/extractions`,
    undefined,
    timeoutMs === undefined ? undefined : { timeout: timeoutMs },
  )

  return response.data
}
