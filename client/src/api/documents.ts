import { apiClient } from "./client";

export type StandardDocumentSummary = {
  id: string;
  workspace_id: string;
  source_type: string;
  title: string | null;
  author: string | null;
  source_created_at: string | null;
  participants: unknown[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export async function getDocuments(
  workspaceId: string,
): Promise<StandardDocumentSummary[]> {
  const response = await apiClient.get<StandardDocumentSummary[]>(
    `/workspaces/${workspaceId}/documents`,
  );

  return response.data;
}

export async function uploadDocuments(
  workspaceId: string,
  files: File[],
): Promise<StandardDocumentSummary[]> {
  const formData = new FormData();

  for (const file of files) {
    formData.append("files", file);
  }

  const response = await apiClient.post<StandardDocumentSummary[]>(
    `/workspaces/${workspaceId}/documents/upload`,
    formData,
  );

  return response.data;
}

export async function deleteDocument(
  workspaceId: string,
  documentId: string,
): Promise<void> {
  await apiClient.delete(`/workspaces/${workspaceId}/documents/${documentId}`);
}
