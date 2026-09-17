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

  const canGenerateBRD =
    Boolean(brdStatus) &&
    ((!brdStatus.has_brd && brdStatus.has_sources) ||
      brdStatus.regeneration_required);

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadDocuments(id!, files),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });

      queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });
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

    try {
      const blob = await exportBRDPdf(id);

      downloadBlob(blob, `${workspace.name} - BRD.pdf`);
    } catch {
      window.alert("Failed to download BRD PDF. Please try again.");
    }
  }

  async function handleDownloadDocx() {
    if (!id) {
      return;
    }

    try {
      const blob = await exportBRDDocx(id);

      downloadBlob(blob, `${workspace.name} - BRD.docx`);
    } catch {
      window.alert("Failed to download BRD DOCX. Please try again.");
    }
  }

  async function handleGenerateBRD() {
    if (!id || !canGenerateBRD || generationStep !== "idle") {
      return;
    }

    try {
      setGenerationError(false);

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

    await updateBRDMutation.mutateAsync(brdData);
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

  function handleDeleteDocument(documentId: string) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this source?",
    );

    if (!confirmed) {
      return;
    }

    deleteMutation.mutate(documentId);
  }

  function handleConnectGmail() {
    connectGmailMutation.mutate();
  }

  function handleDisconnectGmail() {
    const confirmed = window.confirm(
      "Are you sure you want to disconnect Gmail?",
    );

    if (!confirmed) {
      return;
    }

    disconnectGmailMutation.mutate();
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

  if (isWorkspaceLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white">
        <p className="text-base text-[#999999]">Loading workspace...</p>
      </main>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-white px-4 sm:px-8">
        <p className="text-sm font-medium text-black">
          Failed to load workspace.
        </p>

        <Button variant="secondary" onClick={() => navigate("/workspaces")}>
          Back to Workspaces
        </Button>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="print:hidden">
        <TopBar
          left={
            <>
              <Button
                variant="secondary"
                onClick={() => navigate("/workspaces")}
              >
                <ArrowLeft />
                Workspaces
              </Button>

              <div className="min-w-0">
                <h1 className="truncate text-[22px] leading-[25.3px] font-medium tracking-[-0.22px] text-black">
                  {workspace.name}
                </h1>

                {workspace.description && (
                  <p className="truncate text-sm text-[#999999]">
                    {workspace.description}
                  </p>
                )}
              </div>
            </>
          }
          right={
            <Button variant="secondary" onClick={handleSignOut}>
              Sign out
            </Button>
          }
        />
      </div>

      <div className="grid min-h-[calc(100vh-81px)] grid-cols-1 border-t border-black/8 md:h-[calc(100vh-81px)] md:grid-cols-[280px_minmax(0,1fr)_320px] md:overflow-hidden">
        <aside className="border-b border-black/8 bg-white p-6 print:hidden md:border-r md:border-b-0">
          {/* Sources */}
          <section>
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                Sources
              </h2>

              <label
                htmlFor="workspace-sources-upload"
                className="inline-flex h-9 cursor-pointer items-center justify-center gap-1.5 rounded-full bg-black px-5 font-mono text-[16px] leading-4 font-medium tracking-[0.08px] text-white uppercase transition-opacity hover:opacity-80"
              >
                <Upload />
                {uploadMutation.isPending ? "Uploading..." : "Add sources"}
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

            <p className="mt-2 text-xs text-[#999999]">
              Accepts .txt, .pdf, and .docx files.
            </p>

            {isDocumentsLoading && (
              <div className="mt-4 space-y-2" aria-label="Loading sources">
                {[0, 1].map((index) => (
                  <div
                    key={index}
                    className="rounded-[4px] border border-black/8 bg-white p-4"
                  >
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="mt-2 h-3 w-1/3" />
                  </div>
                ))}
              </div>
            )}

            {isDocumentsError && (
              <p className="mt-4 text-sm font-medium text-black">
                Failed to load sources.
              </p>
            )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length === 0 && (
                <p className="mt-4 text-sm text-[#999999]">
                  No uploaded sources yet.
                </p>
              )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length > 0 && (
                <div className="mt-4 space-y-2">
                  {uploadedDocuments.map((document) => (
                    <div
                      key={document.id}
                      className="rounded-[4px] border border-black/8 bg-white p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-start gap-3">
                          <span
                            aria-hidden="true"
                            className="flex size-9 shrink-0 items-center justify-center rounded-full border border-black/8 bg-white text-black"
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

                            <p className="mt-2 inline-flex max-w-full rounded-[4px] border border-black/8 bg-white px-3 py-1 font-mono text-[11px] font-medium tracking-[0.055px] text-black uppercase">
                              <span className="truncate">
                                {document.source_type}
                              </span>
                            </p>
                          </div>
                        </div>

                        <Button
                          variant="secondary"
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
              <p className="mt-4 text-sm font-medium text-black" role="alert">
                {uploadValidationError}
              </p>
            )}

            {uploadMutation.isError && (
              <p className="mt-4 text-sm font-medium text-black" role="alert">
                Failed to upload sources. Please try again.
              </p>
            )}
          </section>

          {/* Gmail */}
          <section className="mt-8 border-t border-black/8 pt-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                Gmail
              </h2>

              {!isGmailStatusLoading &&
                !isGmailStatusError &&
                !gmailStatus?.connected && (
                  <Button
                    variant="secondary"
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
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setIsGmailBrowserOpen(true)}
                    >
                      Browse
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
                  </div>
                )}
            </div>

            {isGmailStatusLoading && (
              <p className="mt-3 text-xs text-[#999999]">
                Checking connection...
              </p>
            )}

            {!isGmailStatusLoading && isGmailStatusError && (
              <p className="mt-3 text-xs font-medium text-black">
                Failed to check Gmail connection.
              </p>
            )}

            {!isGmailStatusLoading &&
              !isGmailStatusError &&
              !gmailStatus?.connected && (
                <p className="mt-3 text-xs text-[#999999]">
                  Connect Gmail to add emails as sources.
                </p>
              )}

            {!isGmailStatusLoading &&
              !isGmailStatusError &&
              gmailStatus?.connected && (
                <>
                  <p className="mt-3 truncate text-xs text-[#999999]">
                    Connected: {gmailStatus.email}
                  </p>

                  {emailDocuments.length === 0 && (
                    <p className="mt-4 text-sm text-[#999999]">
                      No Gmail emails added yet.
                    </p>
                  )}

                  {emailDocuments.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {emailDocuments.map((document) => (
                        <div
                          key={document.id}
                          className="rounded-[4px] border border-black/8 bg-white p-4"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex min-w-0 items-start gap-3">
                              <span
                                aria-hidden="true"
                                className="flex size-9 shrink-0 items-center justify-center rounded-full border border-black/8 bg-white text-black"
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
                                    className="mt-1 truncate text-xs text-[#999999]"
                                    title={document.author}
                                  >
                                    {document.author}
                                  </p>
                                )}
                              </div>
                            </div>

                            <Button
                              variant="secondary"
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
              <p className="mt-3 text-xs font-medium text-black" role="alert">
                Failed to connect Gmail. Please try again.
              </p>
            )}

            {disconnectGmailMutation.isError && (
              <p className="mt-3 text-xs font-medium text-black" role="alert">
                Failed to disconnect Gmail. Please try again.
              </p>
            )}

            {importGmailMutation.isError && (
              <p className="mt-3 text-xs font-medium text-black" role="alert">
                Failed to add Gmail emails as sources. Please try again.
              </p>
            )}
          </section>

          {deleteMutation.isError && (
            <p className="mt-6 text-sm font-medium text-black" role="alert">
              Failed to delete source. Please try again.
            </p>
          )}
        </aside>

        <section className="min-h-0 min-w-0 overflow-y-auto bg-white p-6 print:p-0 sm:p-8">
          <div className="mb-6 flex items-center justify-between print:hidden">
            <h2 className="text-[28px] leading-[32.2px] font-medium tracking-[-0.42px] text-black">
              BRD
            </h2>

            {brdStatus?.has_brd && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button>
                      <Download />
                      Download
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
            <div className="rounded-[4px] border border-black/8 bg-white p-6">
              <ol className="space-y-3">
                {(
                  [
                    ["processing-sources", "Processing sources"],
                    ["preparing-knowledge", "Preparing project knowledge"],
                    ["generating-brd", "Generating BRD"],
                  ] as const
                ).map(([step, label]) => {
                  const order = [
                    "processing-sources",
                    "preparing-knowledge",
                    "generating-brd",
                  ] as const;

                  const isActive = generationStep === step;

                  const isDone =
                    order.indexOf(generationStep as (typeof order)[number]) >
                    order.indexOf(step);

                  return (
                    <li key={step} className="flex items-center gap-3">
                      <span
                        aria-hidden="true"
                        className={
                          isActive
                            ? "flex size-6 items-center justify-center rounded-full bg-black text-white"
                            : isDone
                              ? "size-6 rounded-full bg-black"
                              : "size-6 rounded-full border border-black/8"
                        }
                      >
                        {isActive && <Loader2 className="animate-spin" />}
                      </span>

                      <span
                        className={
                          isActive || isDone
                            ? "text-base font-medium text-black"
                            : "text-base text-[#999999]"
                        }
                      >
                        {label}
                        {isActive ? "..." : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>

              <p className="mt-4 text-sm text-[#999999]">
                This may take a little while.
              </p>
            </div>
          )}

          {generationStep === "idle" && generationError && (
            <div className="mb-6 rounded-[4px] border border-black/8 bg-white p-4">
              <p className="text-sm font-medium text-black" role="alert">
                Failed to generate BRD. Please try again.
              </p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusLoading && (
            <div className="rounded-[4px] border border-black/8 bg-white p-6">
              <p className="text-base text-[#999999]">Checking BRD status...</p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div className="rounded-[4px] border border-black/8 bg-white p-6">
              <p className="text-sm font-medium text-black">
                Failed to load BRD status.
              </p>
            </div>
          )}

          {generationStep === "idle" &&
            !isBRDStatusLoading &&
            !isBRDStatusError &&
            brdStatus &&
            !brdStatus.has_brd && (
              <div className="rounded-[4px] border border-black/8 bg-white p-8 text-center sm:p-12">
                <p className="font-mono text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
                  Getting started
                </p>

                <h3 className="mt-4 text-[22px] leading-[25.3px] font-medium tracking-[-0.22px] text-black">
                  No BRD generated yet.
                </h3>

                {brdStatus.has_sources ? (
                  <>
                    <p className="mx-auto mt-2 max-w-sm text-sm text-[#999999]">
                      Sources are ready for BRD generation.
                    </p>

                    <Button
                      className="mt-4"
                      onClick={handleGenerateBRD}
                      disabled={generationStep !== "idle"}
                    >
                      Generate BRD
                    </Button>
                  </>
                ) : (
                  <p className="mx-auto mt-2 max-w-sm text-sm text-[#999999]">
                    Add sources from the panel to get started.
                  </p>
                )}
              </div>
            )}

          {/* Outdated BRD with manual edits */}
          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required &&
            brdStatus.has_user_edits && (
              <div className="mb-6 rounded-[4px] border border-black/8 bg-white p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-medium text-black">
                      Your BRD needs to be regenerated.
                    </p>

                    <p className="mt-2 text-sm leading-6 text-[#999999]">
                      Your sources have changed since the last BRD generation,
                      and this BRD contains manual changes. Regenerating may
                      overwrite those changes.
                    </p>

                    <p className="mt-2 text-sm leading-6 text-[#999999]">
                      We recommend downloading your current BRD using the
                      Download menu above before regenerating it.
                    </p>
                  </div>

                  <Button
                    onClick={handleGenerateBRD}
                    disabled={generationStep !== "idle"}
                  >
                    Regenerate BRD
                  </Button>
                </div>
              </div>
            )}

          {/* Outdated BRD without manual edits */}
          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required &&
            !brdStatus.has_user_edits && (
              <div className="mb-6 rounded-[4px] border border-black/8 bg-white p-6 print:hidden">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-medium text-black">
                      BRD needs to be regenerated.
                    </p>

                    <p className="mt-1 text-sm text-[#999999]">
                      Your sources have changed since the last BRD generation.
                    </p>
                  </div>

                  <Button
                    onClick={handleGenerateBRD}
                    disabled={generationStep !== "idle"}
                  >
                    Regenerate BRD
                  </Button>
                </div>
              </div>
            )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDLoading && (
            <div
              className="rounded-[4px] border border-black/8 bg-white p-6 sm:p-8"
              aria-label="Loading BRD"
            >
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="mt-4 h-8 w-2/3" />
              <Skeleton className="mt-4 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-5/6" />

              <div className="mt-8 border-t border-black/8 pt-8">
                <Skeleton className="h-5 w-1/4" />
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-4/6" />
              </div>
            </div>
          )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDError && (
            <div className="rounded-[4px] border border-black/8 bg-white p-6">
              <p className="text-sm font-medium text-black">
                Failed to load BRD.
              </p>
            </div>
          )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brd &&
            !isBRDError && (
              <BRDViewer
                data={brd.brd_data}
                onSave={handleSaveBRD}
                isSaving={updateBRDMutation.isPending}
              />
            )}
        </section>

        {id && <BRDQAPanel workspaceId={id} />}
      </div>

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
