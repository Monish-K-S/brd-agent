import { apiClient } from "./client"

export type ProjectKnowledge = {
  id: string
  workspace_id: string
  knowledge_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export async function consolidateProjectKnowledge(
  workspaceId: string,
): Promise<ProjectKnowledge> {
  const response = await apiClient.post<ProjectKnowledge>(
    `/workspaces/${workspaceId}/project-knowledge/consolidate`,
  )

  return response.data
}

export async function getProjectKnowledge(
  workspaceId: string,
): Promise<ProjectKnowledge> {
  const response = await apiClient.get<ProjectKnowledge>(
    `/workspaces/${workspaceId}/project-knowledge`,
  )

  return response.data
}
