import { apiClient } from "./client"

export type BRD = {
  id: string
  workspace_id: string
  brd_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type BRDStatus = {
  has_brd: boolean
  has_new_sources: boolean
  regeneration_required: boolean
}

export async function generateBRD(
  workspaceId: string,
): Promise<BRD> {
  const response = await apiClient.post<BRD>(
    `/workspaces/${workspaceId}/brd/generate`,
  )

  return response.data
}

export async function getBRD(
  workspaceId: string,
): Promise<BRD> {
  const response = await apiClient.get<BRD>(
    `/workspaces/${workspaceId}/brd`,
  )

  return response.data
}

export async function getBRDStatus(
  workspaceId: string,
): Promise<BRDStatus> {
  const response = await apiClient.get<BRDStatus>(
    `/workspaces/${workspaceId}/brd/status`,
  )

  return response.data
}
