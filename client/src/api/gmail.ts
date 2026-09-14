import { apiClient } from "./client";

export type GmailStatus = {
  connected: boolean;
  email: string | null;
};

export type GmailMessageSummary = {
  id: string;
  thread_id: string | null;
  subject: string | null;
  sender: string | null;
  date: string | null;
  snippet: string | null;
};

export type GmailMessageListResponse = {
  messages: GmailMessageSummary[];
};

export type GmailImportResponse = {
  imported: {
    id: string;
    gmail_message_id: string;
    title: string | null;
  }[];
  skipped_message_ids: string[];
};

export async function getGmailStatus(): Promise<GmailStatus> {
  const response = await apiClient.get<GmailStatus>(
    "/integrations/gmail/status",
  );

  return response.data;
}

export async function connectGmail(
  workspaceId: string,
): Promise<string> {
  const response = await apiClient.get<{ authorization_url: string }>(
    "/integrations/gmail/connect",
    {
      params: {
        workspace_id: workspaceId,
      },
    },
  );

  return response.data.authorization_url;
}

export async function disconnectGmail(): Promise<void> {
  await apiClient.delete("/integrations/gmail");
}

export async function getRecentGmailMessages(): Promise<
  GmailMessageSummary[]
> {
  const response = await apiClient.get<GmailMessageListResponse>(
    "/integrations/gmail/messages/recent",
  );

  return response.data.messages;
}

export async function searchGmailMessages(
  query: string,
): Promise<GmailMessageSummary[]> {
  const response = await apiClient.get<GmailMessageListResponse>(
    "/integrations/gmail/messages/search",
    {
      params: {
        q: query,
      },
    },
  );

  return response.data.messages;
}

export async function importGmailMessages(
  workspaceId: string,
  messageIds: string[],
): Promise<GmailImportResponse> {
  const response = await apiClient.post<GmailImportResponse>(
    `/integrations/gmail/workspaces/${workspaceId}/messages/import`,
    {
      message_ids: messageIds,
    },
  );

  return response.data;
}
