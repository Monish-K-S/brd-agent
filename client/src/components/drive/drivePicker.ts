// Thin wrapper over Google's official Picker — the only Drive file-selection
// UI. No custom file browser: the user gets the familiar Drive window.

const PICKER_SCRIPT_URL = "https://apis.google.com/js/api.js";

// Binaries-only: must match DRIVE_DOWNLOAD_MIMETYPES on the backend.
const PICKER_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
].join(",");

let pickerScriptPromise: Promise<void> | null = null;

function getPickerConfig(): { apiKey: string; appId: string } {
  const apiKey = import.meta.env.VITE_GOOGLE_PICKER_API_KEY as
    | string
    | undefined;
  const appId = import.meta.env.VITE_GOOGLE_APP_ID as string | undefined;

  if (!apiKey || !appId) {
    throw new Error(
      "Google Drive picker is not configured. " +
        "Set VITE_GOOGLE_PICKER_API_KEY and VITE_GOOGLE_APP_ID.",
    );
  }

  return { apiKey, appId };
}

export function loadGooglePicker(): Promise<void> {
  if (window.gapi) {
    return new Promise((resolve) => {
      window.gapi!.load("picker", resolve);
    });
  }

  if (!pickerScriptPromise) {
    pickerScriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");

      script.src = PICKER_SCRIPT_URL;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () =>
        reject(new Error("Failed to load Google Picker."));

      document.head.appendChild(script);
    });
  }

  return pickerScriptPromise.then(
    () =>
      new Promise<void>((resolve) => {
        window.gapi!.load("picker", resolve);
      }),
  );
}

export type DrivePickerResult = {
  driveFileId: string;
  name: string;
}[];

type OpenDrivePickerOptions = {
  accessToken: string;
  onPicked: (results: DrivePickerResult) => void;
  onCancel: () => void;
};

export function openDrivePicker({
  accessToken,
  onPicked,
  onCancel,
}: OpenDrivePickerOptions): void {
  const { apiKey, appId } = getPickerConfig();

  const view = new google.picker.View(google.picker.ViewId.DOCS);

  view.setMimeTypes(PICKER_MIME_TYPES);

  const picker = new google.picker.PickerBuilder()
    .setAppId(appId)
    .setOAuthToken(accessToken)
    .setDeveloperKey(apiKey)
    .addView(view)
    .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
    .setTitle("Select from Google Drive")
    // Mirror the Gmail browser dialog (max-w-2xl, max-h-85vh).
    .setSize(672, 560)
    .setCallback((data) => {
      if (data.action === google.picker.Action.PICKED) {
        const picked = (data.docs ?? []).map((document) => ({
          driveFileId: document.id,
          name: document.name,
        }));

        if (picked.length > 0) {
          onPicked(picked);
        } else {
          onCancel();
        }
      } else if (data.action === google.picker.Action.CANCEL) {
        onCancel();
      }
    })
    .build();

  picker.setVisible(true);
}
