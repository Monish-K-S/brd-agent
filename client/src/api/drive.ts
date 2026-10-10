import { apiClient } from "./client";
import { throwIfGoogleReconnectRequired } from "./googleReconnect";

export type DriveStatus = {
  connected: boolean;
  email: string | null;
};

export type DriveImportResponse = {
  imported: {
    id: string;
    drive_file_id: string;
    title: string | null;
  }[];
  skipped_file_ids: string[];
};

export async function getDriveStatus(): Promise<DriveStatus> {
  const response = await apiClient.get<DriveStatus>(
    "/integrations/drive/status",
  );

  return response.data;
}

export async function connectDrive(
  workspaceId: string,
): Promise<string> {
  const response = await apiClient.get<{ authorization_url: string }>(
    "/integrations/drive/connect",
    {
      params: {
        workspace_id: workspaceId,
      },
    },
  );

  const authorizationUrl = response.data.authorization_url;

  let parsed: URL;

  try {
    parsed = new URL(authorizationUrl);
  } catch {
    throw new Error("Invalid Drive authorization URL received.");
  }

  if (
    parsed.protocol !== "https:" ||
    parsed.hostname !== "accounts.google.com"
  ) {
    throw new Error("Invalid Drive authorization URL received.");
  }

  return authorizationUrl;
}

export async function disconnectDrive(): Promise<void> {
  await apiClient.delete("/integrations/drive");
}

export async function getDrivePickerToken(): Promise<string> {
  try {
    const response = await apiClient.get<{ access_token: string }>(
      "/integrations/drive/picker-token",
    );

    return response.data.access_token;
  } catch (error) {
    throwIfGoogleReconnectRequired(error, "drive");
    throw error;
  }
}

export async function importDriveFiles(
  workspaceId: string,
  driveFileIds: string[],
): Promise<DriveImportResponse> {
  try {
    const response = await apiClient.post<DriveImportResponse>(
      `/integrations/drive/workspaces/${workspaceId}/files/import`,
      {
        drive_file_ids: driveFileIds,
      },
    );

    return response.data;
  } catch (error) {
    throwIfGoogleReconnectRequired(error, "drive");
    throw error;
  }
}
