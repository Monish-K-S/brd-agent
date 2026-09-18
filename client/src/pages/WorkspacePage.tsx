import { Suspense, lazy, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { deleteDocument, getDocuments, uploadDocuments } from "@/api/documents";
import { getWorkspace } from "@/api/workspaces";
import {
  generateBRD,
  getBRD,
  getBRDStatus,
  updateBRD,
  exportBRDPdf,
  exportBRDDocx,
} from "@/api/brd";
import { consolidateProjectKnowledge } from "@/api/projectKnowledge";
import { extractDocuments } from "@/api/extractions";
import {
  connectGmail,
  disconnectGmail,
  getGmailStatus,
  importGmailMessages,
} from "@/api/gmail";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  Mail,
  Trash2,
  Upload,
} from "lucide-react";
import { BRDViewer } from "@/components/brd/BRDViewer";
import { BRDQAPanel } from "@/components/brd/BRDQAPanel";
import { TopBar } from "@/components/layout/TopBar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  EmptyState,
  FlashNote,
  StateAlert,
  StatusBadge,
} from "@/components/ui/status";
import { useFlash } from "@/components/ui/use-flash";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const GmailSourceBrowser = lazy(() =>
  import("@/components/gmail/GmailSourceBrowser").then((module) => ({
    default: module.GmailSourceBrowser,
  })),
);

export default function WorkspacePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const { signOut } = useAuth();

  const [isGmailBrowserOpen, setIsGmailBrowserOpen] = useState(false);

  const {
    data: workspace,
    isLoading: isWorkspaceLoading,
    isError: isWorkspaceError,
    refetch: refetchWorkspace,
  } = useQuery({
    queryKey: ["workspace", id],
    queryFn: () => getWorkspace(id!),
    enabled: Boolean(id),
    retry: false,
  });

  const {
    data: documents,
    isLoading: isDocumentsLoading,
    isError: isDocumentsError,
    refetch: refetchDocuments,
  } = useQuery({
    queryKey: ["documents", id],
    queryFn: () => getDocuments(id!),
    enabled: Boolean(id),
    retry: false,
  });

  const {
    data: gmailStatus,
    isLoading: isGmailStatusLoading,
    isError: isGmailStatusError,
    refetch: refetchGmailStatus,
  } = useQuery({
    queryKey: ["gmail-status"],
    queryFn: getGmailStatus,
    enabled: Boolean(id),
    retry: false,
  });

  const {
    data: brdStatus,
    isLoading: isBRDStatusLoading,
    isError: isBRDStatusError,
    refetch: refetchBRDStatus,
  } = useQuery({
    queryKey: ["brd-status", id],
    queryFn: () => getBRDStatus(id!),
    enabled: Boolean(id),
    retry: false,
  });

  const {
    data: brd,
    isLoading: isBRDLoading,
    isError: isBRDError,
    refetch: refetchBRD,
  } = useQuery({
    queryKey: ["brd", id],
    queryFn: () => getBRD(id!),
    enabled: Boolean(id) && Boolean(workspace) && Boolean(brdStatus?.has_brd),
    retry: false,
  });

  type GenerationStep =
    "idle" | "processing-sources" | "preparing-knowledge" | "generating-brd";

  const [generationStep, setGenerationStep] = useState<GenerationStep>("idle");

  const [generationError, setGenerationError] = useState(false);
  const [skippedExtraction, setSkippedExtraction] = useState(false);

  const canGenerateBRD = Boolean(
    brdStatus &&
      ((!brdStatus.has_brd && brdStatus.has_sources) ||
        brdStatus.regeneration_required),
  );

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadDocuments(id!, files),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });

      queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });

      flashSources("Added");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(id!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });

      queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });

      flashSources("Deleted");
    },
  });

  const connectGmailMutation = useMutation({
    mutationFn: () => connectGmail(id!),
    onSuccess: (authorizationUrl) => {
      window.location.assign(authorizationUrl);
    },
  });

  const disconnectGmailMutation = useMutation({
    mutationFn: disconnectGmail,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["gmail-status"],
      });
    },
  });

  const importGmailMutation = useMutation({
    mutationFn: (messageIds: string[]) => importGmailMessages(id!, messageIds),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });

      queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });

      setIsGmailBrowserOpen(false);
      flashSources("Added");
    },
  });

  const updateBRDMutation = useMutation({
    mutationFn: (brdData: Parameters<typeof updateBRD>[1]) =>
      updateBRD(id!, brdData),
    onSuccess: (updatedBRD) => {
      queryClient.setQueryData(["brd", id], updatedBRD);

      queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });
    },
  });

  const [sourcesNoteKey, showSourcesNote] = useFlash();
  const [sourcesNoteText, setSourcesNoteText] = useState("Added");
  const [generatedNoteKey, showGeneratedNote] = useFlash();
  const [savedNoteKey, showSavedNote] = useFlash();
  const [exportFailed, setExportFailed] = useState(false);

  function flashSources(text: string) {
    setSourcesNoteText(text);
    showSourcesNote();
  }

  const MAX_EXPORT_NAME_CHARS = 80;

  function safeExportFilename(
    workspaceName: string,
    extension: string,
  ): string {
    let stem = workspaceName.trim() || "BRD";

    // eslint-disable-next-line no-control-regex
    stem = stem.replace(/[\x00-\x1f\x7f"\\/]/g, "");

    stem = stem.replace(/\s+/g, " ").replace(/^[./]+/, "") || "BRD";

    if (stem.length > MAX_EXPORT_NAME_CHARS) {
      stem = stem.slice(0, MAX_EXPORT_NAME_CHARS).trimEnd() || "BRD";
    }

    return `${stem} - BRD.${extension}`;
  }

  function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename;

    document.body.appendChild(link);
    link.click();
    link.remove();

    window.URL.revokeObjectURL(url);
  }

  async function handleDownloadPdf() {
    if (!id) {
      return;
    }

    setExportFailed(false);

    try {
      const blob = await exportBRDPdf(id);

      downloadBlob(blob, safeExportFilename(workspace?.name ?? "BRD", "pdf"));
    } catch {
      setExportFailed(true);
    }
  }

  async function handleDownloadDocx() {
    if (!id) {
      return;
    }

    setExportFailed(false);

    try {
      const blob = await exportBRDDocx(id);

      downloadBlob(blob, safeExportFilename(workspace?.name ?? "BRD", "docx"));
    } catch {
      setExportFailed(true);
    }
  }

  async function handleGenerateBRD() {
    if (!id || !canGenerateBRD || generationStep !== "idle") {
      return;
    }

    try {
      setGenerationError(false);
      setSkippedExtraction(!brdStatus?.has_new_sources);

      if (brdStatus?.has_new_sources) {
        setGenerationStep("processing-sources");
        await extractDocuments(id);
      }

      setGenerationStep("preparing-knowledge");
      await consolidateProjectKnowledge(id);

      setGenerationStep("generating-brd");
      await generateBRD(id);

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd", id],
        }),
      ]);

      setGenerationStep("idle");
      showGeneratedNote();
    } catch {
      setGenerationStep("idle");
      setGenerationError(true);

      await queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });
    }
  }

  async function handleSaveBRD(brdData: Parameters<typeof updateBRD>[1]) {
    if (!id) {
      return;
    }

    try {
      await updateBRDMutation.mutateAsync(brdData);
      showSavedNote();
    } catch {
      // updateBRDMutation.isError surfaces the failure in the viewer.
    }
  }

  async function handleSignOut() {
    await signOut();
    navigate("/auth", { replace: true });
  }

  const MAX_UPLOAD_FILES = 10;
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
  const ALLOWED_EXTENSIONS = [".txt", ".pdf", ".docx"];

  const [uploadValidationError, setUploadValidationError] = useState<
    string | null
  >(null);

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);

    // Allow selecting the same file again after an upload.
    event.target.value = "";

    if (files.length === 0) {
      return;
    }

    setUploadValidationError(null);

    if (files.length > MAX_UPLOAD_FILES) {
      setUploadValidationError(
        `Too many files: ${files.length}. Maximum ${MAX_UPLOAD_FILES} files per upload.`,
      );
      return;
    }

    for (const file of files) {
      const suffix = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;

      if (!ALLOWED_EXTENSIONS.includes(suffix)) {
        setUploadValidationError(
          `Unsupported file type: ${file.name}. Supported types: .txt, .pdf, .docx`,
        );
        return;
      }

      if (file.size > MAX_UPLOAD_BYTES) {
        setUploadValidationError(
          `File too large: ${file.name} (max 10MB)`,
        );
        return;
      }
    }

    uploadMutation.mutate(files);
  }

  const [pendingDeleteDocumentId, setPendingDeleteDocumentId] = useState<
    string | null
  >(null);
  const [confirmDisconnectOpen, setConfirmDisconnectOpen] = useState(false);

  function handleDeleteDocument(documentId: string) {
    setPendingDeleteDocumentId(documentId);
  }

  function handleConfirmDeleteDocument() {
    if (!pendingDeleteDocumentId || deleteMutation.isPending) {
      return;
    }

    deleteMutation.mutate(pendingDeleteDocumentId);
    setPendingDeleteDocumentId(null);
  }

  function handleConnectGmail() {
    connectGmailMutation.mutate();
  }

  function handleDisconnectGmail() {
    setConfirmDisconnectOpen(true);
  }

  function handleConfirmDisconnectGmail() {
    if (disconnectGmailMutation.isPending) {
      return;
    }

    disconnectGmailMutation.mutate();
    setConfirmDisconnectOpen(false);
  }

  function handleImportGmailMessages(messageIds: string[]) {
    if (!id || messageIds.length === 0) {
      return;
    }

    importGmailMutation.mutate(messageIds);
  }

  const uploadedDocuments =
    documents?.filter((document) => document.source_type !== "email") ?? [];

  const emailDocuments =
    documents?.filter((document) => document.source_type === "email") ?? [];

  function readPanelPreference(key: string): boolean {
    try {
      return localStorage.getItem(key) !== "0";
    } catch {
      return true;
    }
  }

  function writePanelPreference(key: string, open: boolean) {
    try {
      localStorage.setItem(key, open ? "1" : "0");
    } catch {
      // Persistence is a nicety; ignore failures.
    }
  }

  const [sourcesOpen, setSourcesOpen] = useState(() =>
    readPanelPreference("brd.sourcesOpen"),
  );
  const [qaOpen, setQaOpen] = useState(() =>
    readPanelPreference("brd.qaOpen"),
  );

  function toggleSources() {
    setSourcesOpen((open) => {
      writePanelPreference("brd.sourcesOpen", !open);
      return !open;
    });
  }

  function toggleQa() {
    setQaOpen((open) => {
      writePanelPreference("brd.qaOpen", !open);
      return !open;
    });
  }

  const hasSources =
    (documents?.length ?? 0) > 0 || Boolean(brdStatus?.has_sources);

  const brdStateLabel = !brdStatus
    ? null
    : !brdStatus.has_brd
      ? hasSources
        ? "Ready to generate"
        : "No sources yet"
      : brdStatus.regeneration_required
        ? "New sources available"
        : "Up to date";

  if (isWorkspaceLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white">
        <p className="text-base text-[#5e5e5e]">Loading...</p>
      </main>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-white px-4 sm:px-8">
        <StateAlert className="max-w-md">
          Something went wrong. Please try again.
        </StateAlert>

        <div className="flex gap-3">
          <Button variant="subtle" onClick={() => refetchWorkspace()}>
            Retry
          </Button>

          <Button variant="subtle" onClick={() => navigate("/workspaces")}>
            Back to Workspaces
          </Button>
        </div>
      </main>
    );
  }

  const gridCols =
    !sourcesOpen && !qaOpen
      ? "md:grid-cols-[56px_minmax(0,1fr)_56px]"
      : !sourcesOpen
        ? "md:grid-cols-[56px_minmax(0,1fr)_18%]"
        : !qaOpen
          ? "md:grid-cols-[22%_minmax(0,1fr)_56px]"
          : "md:grid-cols-[22%_minmax(0,1fr)_18%]";

  return (
    <main className="min-h-screen bg-white text-black">
      <div className="print:hidden">
        <TopBar
          left={
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/workspaces")}
                aria-label="Back to workspaces"
              >
                <ArrowLeft />
                <span className="hidden sm:inline">Workspaces</span>
              </Button>

              <div className="min-w-0">
                <h1 className="truncate text-base leading-6 font-medium text-black">
                  {workspace.name}
                </h1>

                {workspace.description && (
                  <p className="truncate text-xs leading-5 text-[#5e5e5e]">
                    {workspace.description}
                  </p>
                )}
              </div>
            </>
          }
          right={
            <Button variant="subtle" size="sm" onClick={handleSignOut}>
              Sign out
            </Button>
          }
        />
      </div>

      <div
        className={`grid min-h-[calc(100vh-65px)] grid-cols-1 md:h-[calc(100vh-65px)] md:overflow-hidden ${gridCols}`}
      >
        <aside className="border-b border-black/10 bg-white p-4 print:hidden md:overflow-y-auto md:border-r md:border-b-0">
          {!sourcesOpen ? (
            <button
              type="button"
              onClick={toggleSources}
              aria-label="Show sources"
              title="Show sources"
              className="flex size-9 items-center justify-center rounded-full bg-[#efefef] text-black transition-colors hover:bg-[#e2e2e2]"
            >
              <ChevronRight />
            </button>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-medium text-black">
                  Sources
                  {(documents?.length ?? 0) > 0 && (
                    <span className="ml-2 text-sm font-normal text-[#afafaf]">
                      {documents?.length}
                    </span>
                  )}
                </h2>

                <button
                  type="button"
                  onClick={toggleSources}
                  aria-label="Hide sources"
                  aria-expanded="true"
                  title="Hide sources"
                  className="flex size-9 items-center justify-center rounded-full text-black transition-colors hover:bg-black/5"
                >
                  <ChevronLeft />
                </button>
              </div>

          <section className="mt-4">
            <div>
              <label
                htmlFor="workspace-sources-upload"
                className="inline-flex h-11 cursor-pointer items-center justify-center gap-1.5 rounded-full bg-black px-5 text-base font-medium text-white transition-colors hover:bg-black/80"
              >
                <Upload />
                {uploadMutation.isPending ? "Uploading..." : "Add"}
              </label>

              <input
                id="workspace-sources-upload"
                type="file"
                multiple
                accept=".txt,.pdf,.docx"
                className="sr-only"
                onChange={handleFileChange}
                disabled={uploadMutation.isPending}
              />
            </div>

            <p className="mt-2 text-xs leading-5 text-[#afafaf]">
              .txt, .pdf, .docx
            </p>

            {isDocumentsLoading && (
              <div className="mt-4 space-y-2" aria-label="Loading sources">
                {[0, 1].map((index) => (
                  <div
                    key={index}
                    className="rounded-2xl bg-[#efefef] p-4"
                  >
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="mt-2 h-3 w-1/3" />
                  </div>
                ))}
              </div>
            )}

            {isDocumentsError && (
              <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-4">
                <p className="text-sm text-black">
                  Couldn&apos;t load sources.
                </p>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchDocuments()}
                >
                  Retry
                </Button>
              </div>
            )}

            {sourcesNoteKey > 0 && (
              <FlashNote key={sourcesNoteKey} className="mt-4">
                {sourcesNoteText}
              </FlashNote>
            )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length === 0 &&
              emailDocuments.length === 0 && (
                <p className="mt-4 text-sm leading-5 text-[#5e5e5e]">
                  Nothing here yet.
                </p>
              )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length > 0 && (
                <div className="mt-4 space-y-2">
                  {uploadedDocuments.map((document) => (
                    <div
                      key={document.id}
                      className="rounded-2xl bg-[#efefef] p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-start gap-3">
                          <span
                            aria-hidden="true"
                            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white text-black"
                          >
                            <FileText />
                          </span>

                          <div className="min-w-0">
                            <p
                              className="line-clamp-2 text-sm leading-5 font-medium text-black"
                              title={document.title || "Untitled source"}
                            >
                              {document.title || "Untitled source"}
                            </p>

                            <div className="mt-2">
                              <StatusBadge tone="neutral">
                                {document.source_type}
                              </StatusBadge>
                            </div>
                          </div>
                        </div>

                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label="Delete source"
                          title="Delete source"
                          onClick={() => handleDeleteDocument(document.id)}
                          disabled={
                            deleteMutation.isPending &&
                            deleteMutation.variables === document.id
                          }
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

            {uploadValidationError && (
              <StateAlert className="mt-4">
                {uploadValidationError}
              </StateAlert>
            )}

            {uploadMutation.isError && (
              <StateAlert className="mt-4">
                Upload failed. Try again.
              </StateAlert>
            )}
          </section>

          {/* Gmail */}
          <section className="mt-8 border-t border-black/10 pt-6">
            <h2 className="text-base font-medium text-black">Gmail</h2>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {!isGmailStatusLoading &&
                !isGmailStatusError &&
                !gmailStatus?.connected && (
                  <Button
                    variant="subtle"
                    size="sm"
                    onClick={handleConnectGmail}
                    disabled={connectGmailMutation.isPending}
                  >
                    {connectGmailMutation.isPending
                      ? "Connecting..."
                      : "Connect"}
                  </Button>
                )}

              {!isGmailStatusLoading &&
                !isGmailStatusError &&
                gmailStatus?.connected && (
                  <>
                    <Button
                      variant="subtle"
                      size="sm"
                      onClick={() => setIsGmailBrowserOpen(true)}
                    >
                      Import
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDisconnectGmail}
                      disabled={disconnectGmailMutation.isPending}
                    >
                      {disconnectGmailMutation.isPending
                        ? "Disconnecting..."
                        : "Disconnect"}
                    </Button>
                  </>
                )}
            </div>

            {isGmailStatusLoading && (
              <p className="mt-3 text-xs text-[#5e5e5e]">Checking...</p>
            )}

            {!isGmailStatusLoading && isGmailStatusError && (
              <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-3">
                <p className="text-sm text-black">
                  Couldn&apos;t check Gmail.
                </p>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchGmailStatus()}
                >
                  Retry
                </Button>
              </div>
            )}

            {!isGmailStatusLoading &&
              !isGmailStatusError &&
              gmailStatus?.connected && (
                <>
                  <p className="mt-3 truncate text-xs text-[#afafaf]">
                    {gmailStatus.email}
                  </p>

                  {emailDocuments.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {emailDocuments.map((document) => (
                        <div
                          key={document.id}
                          className="rounded-2xl bg-[#efefef] p-4"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex min-w-0 items-start gap-3">
                              <span
                                aria-hidden="true"
                                className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white text-black"
                              >
                                <Mail />
                              </span>

                              <div className="min-w-0">
                                <p
                                  className="line-clamp-2 text-sm leading-5 font-medium text-black"
                                  title={document.title || "No subject"}
                                >
                                  {document.title || "No subject"}
                                </p>

                                {document.author && (
                                  <p
                                    className="mt-1 truncate text-xs text-[#5e5e5e]"
                                    title={document.author}
                                  >
                                    {document.author}
                                  </p>
                                )}
                              </div>
                            </div>

                            <Button
                              variant="ghost"
                              size="icon-sm"
                              aria-label="Delete source"
                              title="Delete source"
                              onClick={() => handleDeleteDocument(document.id)}
                              disabled={
                                deleteMutation.isPending &&
                                deleteMutation.variables === document.id
                              }
                            >
                              <Trash2 />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

            {connectGmailMutation.isError && (
              <StateAlert className="mt-3">
                Connection failed. Try again.
              </StateAlert>
            )}

            {disconnectGmailMutation.isError && (
              <StateAlert className="mt-3">
                Couldn&apos;t disconnect.
              </StateAlert>
            )}

            {importGmailMutation.isError && (
              <StateAlert className="mt-3">
                Import failed. Try again.
              </StateAlert>
            )}
          </section>

          {deleteMutation.isError && (
            <StateAlert className="mt-6">
              Couldn&apos;t delete it.
            </StateAlert>
          )}
            </>
          )}
        </aside>

        <section className="min-h-0 min-w-0 overflow-y-auto bg-white p-6 print:p-0 sm:p-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 print:hidden">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl leading-8 font-bold text-black">BRD</h2>

              {brdStateLabel && (
                <StatusBadge tone="neutral">{brdStateLabel}</StatusBadge>
              )}
            </div>

            {brdStatus?.has_brd && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button variant="subtle">
                      <Download />
                      Export
                    </Button>
                  }
                />

                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleDownloadPdf}>
                    PDF
                  </DropdownMenuItem>

                  <DropdownMenuItem onClick={handleDownloadDocx}>
                    DOCX
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {generationStep !== "idle" && (
            <div className="rounded-2xl bg-[#efefef] p-6 print:hidden">
              <ol className="space-y-3">
                {(
                  [
                    ["processing-sources", "Reading sources"],
                    ["preparing-knowledge", "Organizing knowledge"],
                    ["generating-brd", "Writing BRD"],
                  ] as const
                ).map(([step, label]) => {
                  const order = [
                    "processing-sources",
                    "preparing-knowledge",
                    "generating-brd",
                  ] as const;

                  const isActive = generationStep === step;

                  const isDone =
                    (step === "processing-sources" && skippedExtraction) ||
                    order.indexOf(generationStep as (typeof order)[number]) >
                      order.indexOf(step);

                  return (
                    <li key={step} className="flex items-center gap-3">
                      {isActive ? (
                        <Loader2
                          aria-hidden="true"
                          className="size-4 animate-spin text-black"
                        />
                      ) : (
                        <span
                          aria-hidden="true"
                          className={
                            isDone
                              ? "size-2 rounded-full bg-black"
                              : "size-2 rounded-full border border-black/20"
                          }
                        />
                      )}

                      <span
                        className={
                          isActive || isDone
                            ? "text-base font-medium text-black"
                            : "text-base text-[#5e5e5e]"
                        }
                      >
                        {label}
                        {isActive ? "..." : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </div>
          )}

          {generationStep === "idle" && generationError && (
            <StateAlert className="mb-6 print:hidden">
              Generation failed. Try again.
            </StateAlert>
          )}

          {generationStep === "idle" && isBRDStatusLoading && (
            <div className="rounded-2xl bg-[#efefef] p-6 print:hidden">
              <p className="text-base text-[#5e5e5e]">Loading...</p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-4 print:hidden">
              <p className="text-sm text-black">Something went wrong.</p>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetchBRDStatus()}
              >
                Retry
              </Button>
            </div>
          )}

          {generationStep === "idle" &&
            !isBRDStatusLoading &&
            !isBRDStatusError &&
            brdStatus &&
            !brdStatus.has_brd && (
              <EmptyState
                title="No BRD yet"
                description={
                  brdStatus.has_sources
                    ? "Generate it from your sources."
                    : "Add sources first."
                }
                action={
                  brdStatus.has_sources ? (
                    <Button onClick={handleGenerateBRD}>Generate</Button>
                  ) : undefined
                }
                className="print:hidden"
              />
            )}

          {/* Outdated BRD */}
          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required && (
              <div className="mb-6 rounded-2xl bg-[#efefef] p-6 print:hidden">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-medium text-black">
                      New sources available.
                    </p>

                    {brdStatus.has_user_edits && (
                      <p className="mt-1 text-sm leading-5 text-[#5e5e5e]">
                        Regenerating may overwrite your edits. Export a copy
                        first if you need it.
                      </p>
                    )}
                  </div>

                  <Button
                    onClick={handleGenerateBRD}
                    disabled={generationStep !== "idle"}
                  >
                    Regenerate
                  </Button>
                </div>
              </div>
            )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDLoading && (
            <div
              className="rounded-2xl bg-[#efefef] p-6 sm:p-8"
              aria-label="Loading BRD"
            >
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="mt-4 h-8 w-2/3" />
              <Skeleton className="mt-4 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-5/6" />

              <div className="mt-8 border-t border-black/10 pt-8">
                <Skeleton className="h-5 w-1/4" />
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-4/6" />
              </div>
            </div>
          )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDError && (
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-4 print:hidden">
              <p className="text-sm text-black">Something went wrong.</p>

              <Button variant="ghost" size="sm" onClick={() => refetchBRD()}>
                Retry
              </Button>
            </div>
          )}

          {exportFailed && (
            <StateAlert className="mb-6 print:hidden">
              Export failed. Try again.
            </StateAlert>
          )}

          <div className="flex flex-wrap items-center gap-2 print:hidden">
            {generatedNoteKey > 0 && (
              <FlashNote key={generatedNoteKey} className="mb-6">
                Done
              </FlashNote>
            )}
            {savedNoteKey > 0 && (
              <FlashNote key={savedNoteKey} className="mb-6">
                Saved
              </FlashNote>
            )}
          </div>

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brd &&
            !isBRDError && (
              <BRDViewer
                data={brd.brd_data}
                meta={{
                  createdAt: brd.created_at,
                  updatedAt: brd.updated_at,
                  userEditedAt: brd.user_edited_at,
                }}
                onSave={handleSaveBRD}
                isSaving={updateBRDMutation.isPending}
                saveFailed={updateBRDMutation.isError}
              />
            )}
        </section>

        {id &&
          (qaOpen ? (
            <BRDQAPanel workspaceId={id} onCollapse={toggleQa} />
          ) : (
            <div className="border-t border-black/10 bg-white p-4 print:hidden md:border-t-0 md:border-l">
              <button
                type="button"
                onClick={toggleQa}
                aria-label="Show Q&A"
                title="Show Q&A"
                className="flex size-9 items-center justify-center rounded-full bg-[#efefef] text-black transition-colors hover:bg-[#e2e2e2]"
              >
                <ChevronLeft />
              </button>
            </div>
          ))}
      </div>

      <Dialog
        open={pendingDeleteDocumentId !== null}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) {
            setPendingDeleteDocumentId(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this source?</DialogTitle>

            <DialogDescription>
              This can&apos;t be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
              <Button
                type="button"
                variant="subtle"
                onClick={() => setPendingDeleteDocumentId(null)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>

              <Button
                type="button"
                variant="destructive"
                onClick={handleConfirmDeleteDocument}
                disabled={deleteMutation.isPending}
              >
                Delete
              </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDisconnectOpen} onOpenChange={setConfirmDisconnectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Gmail?</DialogTitle>

            <DialogDescription>
              Imported emails stay. This can&apos;t be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
              <Button
                type="button"
                variant="subtle"
                onClick={() => setConfirmDisconnectOpen(false)}
                disabled={disconnectGmailMutation.isPending}
              >
                Cancel
              </Button>

            <Button
              type="button"
              variant="destructive"
              onClick={handleConfirmDisconnectGmail}
              disabled={disconnectGmailMutation.isPending}
            >
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {isGmailBrowserOpen && (
        <Suspense fallback={null}>
          <GmailSourceBrowser
            onClose={() => {
              if (!importGmailMutation.isPending) {
                setIsGmailBrowserOpen(false);
              }
            }}
            onImport={handleImportGmailMessages}
            isImporting={importGmailMutation.isPending}
          />
        </Suspense>
      )}
    </main>
  );
}
