import { isAxiosError } from "axios";

export type GoogleConnector = "gmail" | "drive";

/**
 * Thrown by the gmail/drive API wrappers when the backend reports a
 * dead grant (409 + reconnect_required). Callers turn this into a
 * "Reconnect" CTA instead of a generic failure message.
 */
export class GoogleReconnectRequiredError extends Error {
  connector: GoogleConnector;

  constructor(connector: GoogleConnector) {
    super("Google connection expired. Reconnect to continue.");
    this.name = "GoogleReconnectRequiredError";
    this.connector = connector;
  }
}

export function throwIfGoogleReconnectRequired(
  error: unknown,
  connector: GoogleConnector,
): void {
  if (isAxiosError(error) && error.response?.status === 409) {
    const data = error.response.data as
      | { reconnect_required?: unknown; connector?: unknown }
      | undefined;

    if (
      data?.reconnect_required === true &&
      data?.connector === connector
    ) {
      throw new GoogleReconnectRequiredError(connector);
    }
  }
}

export function isGoogleReconnectRequiredError(
  error: unknown,
  connector?: GoogleConnector,
): error is GoogleReconnectRequiredError {
  return (
    error instanceof GoogleReconnectRequiredError &&
    (!connector || error.connector === connector)
  );
}
