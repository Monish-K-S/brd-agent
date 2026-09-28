declare namespace google {
  namespace picker {
    enum Action {
      PICKED = "picked",
      CANCEL = "cancel",
    }

    enum ViewId {
      DOCS = "all",
    }

    enum Feature {
      MULTISELECT_ENABLED = "multiselect",
    }

    interface Document {
      id: string;
      name: string;
      mimeType: string;
    }

    interface Response {
      action: Action;
      docs?: Document[];
    }

    class View {
      constructor(viewId: ViewId);
      setMimeTypes(mimeTypes: string): View;
    }

    class PickerBuilder {
      setAppId(appId: string): PickerBuilder;
      setOAuthToken(token: string): PickerBuilder;
      setDeveloperKey(key: string): PickerBuilder;
      addView(view: View): PickerBuilder;
      setCallback(callback: (data: Response) => void): PickerBuilder;
      setTitle(title: string): PickerBuilder;
      setSize(width: number, height: number): PickerBuilder;
      enableFeature(feature: Feature): PickerBuilder;
      build(): Picker;
    }

    interface Picker {
      setVisible(visible: boolean): void;
    }

    const Action: typeof Action;
    const ViewId: typeof ViewId;
    const Feature: typeof Feature;
    const View: typeof View;
    const PickerBuilder: typeof PickerBuilder;
  }
}

interface GapiClient {
  load(api: "picker", callback: () => void): void;
}

interface Window {
  gapi?: GapiClient;
}
