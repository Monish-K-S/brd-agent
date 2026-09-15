import { apiClient } from "./client";
import type { BRDData } from "@/components/brd/BRDViewer";

export type BRD = {
  id: string;
  workspace_id: string;
  brd_data: BRDData;
  created_at: string;
  updated_at: string;
  user_edited_at: string | null;
};

export type BRDStatus = {
  has_brd: boolean;
  has_sources: boolean;
  has_new_sources: boolean;
  regeneration_required: boolean;
  has_user_edits: boolean;
};

export type BRDQASource = {
  id: string;
  title: string | null;
  source_type: string;
};

export type BRDQAResponse = {
  answer: string;
  sources: BRDQASource[];
};

export async function generateBRD(workspaceId: string): Promise<BRD> {
  const response = await apiClient.post<BRD>(
    `/workspaces/${workspaceId}/brd/generate`,
  );

  return response.data;
}

export async function getBRD(workspaceId: string): Promise<BRD> {
  const response = await apiClient.get<BRD>(`/workspaces/${workspaceId}/brd`);

  return response.data;
}

export async function updateBRD(
  workspaceId: string,
  brdData: BRDData,
): Promise<BRD> {
  const response = await apiClient.put<BRD>(`/workspaces/${workspaceId}/brd`, {
    brd_data: brdData,
  });

  return response.data;
}

export async function getBRDStatus(workspaceId: string): Promise<BRDStatus> {
  const response = await apiClient.get<BRDStatus>(
    `/workspaces/${workspaceId}/brd/status`,
  );

  return response.data;
}

export async function askBRD(
  workspaceId: string,
  question: string,
): Promise<BRDQAResponse> {
  const response = await apiClient.post<BRDQAResponse>(
    `/workspaces/${workspaceId}/brd/ask`,
    {
      question,
    },
  );

  return response.data;
}

export async function exportBRDPdf(workspaceId: string): Promise<Blob> {
  const response = await apiClient.get(
    `/workspaces/${workspaceId}/brd/export/pdf`,
    {
      responseType: "blob",
    },
  );

  return response.data;
}

export async function exportBRDDocx(workspaceId: string): Promise<Blob> {
  const response = await apiClient.get(
    `/workspaces/${workspaceId}/brd/export/docx`,
    {
      responseType: "blob",
    },
  );

  return response.data;
}
