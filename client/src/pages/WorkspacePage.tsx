import { useState } from "react";
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
import { BRDViewer } from "@/components/brd/BRDViewer";
import { GmailSourceBrowser } from "@/components/gmail/GmailSourceBrowser";

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
    enabled: Boolean(id) && Boolean(workspace),
    retry: false,
  });

  const {
    data: gmailStatus,
    isLoading: isGmailStatusLoading,
    isError: isGmailStatusError,
  } = useQuery({
    queryKey: ["gmail-status"],
    queryFn: getGmailStatus,
    enabled: Boolean(workspace),
    retry: false,
  });

  const {
    data: brdStatus,
    isLoading: isBRDStatusLoading,
    isError: isBRDStatusError,
  } = useQuery({
    queryKey: ["brd-status", id],
    queryFn: () => getBRDStatus(id!),
    enabled: Boolean(id) && Boolean(workspace),
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
    | "idle"
    | "processing-sources"
    | "preparing-knowledge"
    | "generating-brd";

  const [generationStep, setGenerationStep] =
    useState<GenerationStep>("idle");

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
      queryClient.setQueryData(
        ["brd", id],
        updatedBRD,
      );

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

      await queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });

      await queryClient.invalidateQueries({
        queryKey: ["brd", id],
      });

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

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);

    if (files.length === 0) {
      return;
    }

    uploadMutation.mutate(files);

    // Allow selecting the same file again after an upload.
    event.target.value = "";
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
        <p className="text-base text-[#5e5e5e]">Loading workspace...</p>
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
      <header className="flex items-center justify-between bg-white px-4 py-4 sm:px-8">
        <div className="flex items-center gap-4">
          <Button variant="secondary" onClick={() => navigate("/workspaces")}>
            ← Workspaces
          </Button>

          <div>
            <h1 className="text-xl font-bold tracking-tight text-black">
              {workspace.name}
            </h1>

            {workspace.description && (
              <p className="text-sm text-[#5e5e5e]">{workspace.description}</p>
            )}
          </div>
        </div>

        <Button variant="secondary" onClick={handleSignOut}>
          Sign out
        </Button>
      </header>

      <div className="grid min-h-[calc(100vh-81px)] grid-cols-1 border-t border-[#e2e2e2] md:grid-cols-[280px_1fr]">
        <aside className="border-b border-[#e2e2e2] bg-white p-6 md:border-r md:border-b-0">
          {/* Sources */}
          <section>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xs font-medium tracking-wide text-[#5e5e5e] uppercase">
                Sources
              </h2>

              <label
                htmlFor="workspace-sources-upload"
                className="inline-flex h-9 cursor-pointer items-center justify-center rounded-full bg-black px-4 text-sm font-medium text-white transition-colors hover:bg-[#282828]"
              >
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

            {isDocumentsLoading && (
              <p className="mt-4 text-sm text-[#5e5e5e]">Loading sources...</p>
            )}

            {isDocumentsError && (
              <p className="mt-4 text-sm font-medium text-black">
                Failed to load sources.
              </p>
            )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length === 0 && (
                <p className="mt-4 text-sm text-[#5e5e5e]">
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
                      className="rounded-2xl border border-[#e2e2e2] bg-white p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-black">
                            {document.title || "Untitled source"}
                          </p>

                          <p className="mt-1 text-xs text-[#afafaf]">
                            {document.source_type}
                          </p>
                        </div>

                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleDeleteDocument(document.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

            {uploadMutation.isError && (
              <p className="mt-4 text-sm font-medium text-black" role="alert">
                Failed to upload sources. Please try again.
              </p>
            )}
          </section>

          {/* Gmail */}
          <section className="mt-8 border-t border-[#e2e2e2] pt-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xs font-medium tracking-wide text-[#5e5e5e] uppercase">
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
              <p className="mt-3 text-xs text-[#5e5e5e]">
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
                <p className="mt-3 text-xs text-[#5e5e5e]">
                  Connect Gmail to add emails as sources.
                </p>
              )}

            {!isGmailStatusLoading &&
              !isGmailStatusError &&
              gmailStatus?.connected && (
                <>
                  <p className="mt-3 truncate text-xs text-[#5e5e5e]">
                    Connected: {gmailStatus.email}
                  </p>

                  {emailDocuments.length === 0 && (
                    <p className="mt-4 text-sm text-[#5e5e5e]">
                      No Gmail emails added yet.
                    </p>
                  )}

                  {emailDocuments.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {emailDocuments.map((document) => (
                        <div
                          key={document.id}
                          className="rounded-2xl border border-[#e2e2e2] bg-white p-4"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="truncate text-sm font-medium text-black">
                                {document.title || "No subject"}
                              </p>

                              {document.author && (
                                <p className="mt-1 truncate text-xs text-[#5e5e5e]">
                                  {document.author}
                                </p>
                              )}

                              {document.source_created_at && (
                                <p className="mt-1 text-xs text-[#afafaf]">
                                  {new Date(
                                    document.source_created_at,
                                  ).toLocaleDateString()}
                                </p>
                              )}
                            </div>

                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() =>
                                handleDeleteDocument(document.id)
                              }
                              disabled={deleteMutation.isPending}
                            >
                              Delete
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

          {/* Google Meet */}
          <section className="mt-8 border-t border-[#e2e2e2] pt-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xs font-medium tracking-wide text-[#5e5e5e] uppercase">
                Google Meet
              </h2>
            </div>

            <p className="mt-3 text-sm text-[#5e5e5e]">
              No meeting transcripts yet.
            </p>
          </section>

          {deleteMutation.isError && (
            <p className="mt-6 text-sm font-medium text-black" role="alert">
              Failed to delete source. Please try again.
            </p>
          )}
        </aside>

        <section className="bg-[#f3f3f3] p-6 sm:p-8">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-bold tracking-tight text-black">
              BRD
            </h2>

            {brdStatus?.has_brd && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button className="shadow-level-3">Download</Button>
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
            <div className="rounded-2xl border border-[#e2e2e2] bg-white p-6">
              <p className="text-base font-medium text-black">
                {generationStep === "processing-sources" &&
                  "Processing sources..."}

                {generationStep === "preparing-knowledge" &&
                  "Preparing project knowledge..."}

                {generationStep === "generating-brd" && "Generating BRD..."}
              </p>

              <p className="mt-2 text-sm text-[#5e5e5e]">
                This may take a little while.
              </p>
            </div>
          )}

          {generationStep === "idle" && generationError && (
            <div className="mb-6 rounded-2xl border border-[#e2e2e2] bg-white p-4">
              <p
                className="text-sm font-medium text-black"
                role="alert"
              >
                Failed to generate BRD. Please try again.
              </p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusLoading && (
            <div className="rounded-2xl border border-[#e2e2e2] bg-white p-6">
              <p className="text-base text-[#5e5e5e]">
                Checking BRD status...
              </p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div className="rounded-2xl border border-[#e2e2e2] bg-white p-6">
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
              <div className="rounded-2xl bg-[#efefef] p-8 text-center shadow-level-2">
                <p className="text-base text-[#5e5e5e]">
                  No BRD generated yet.
                </p>

                {brdStatus.has_sources && (
                  <>
                    <p className="mt-2 text-sm text-[#5e5e5e]">
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
                )}
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required && (
              <div className="mb-6 rounded-2xl border border-[#e2e2e2] bg-white p-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-medium text-black">
                      BRD needs to be regenerated.
                    </p>

                    <p className="mt-1 text-sm text-[#5e5e5e]">
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

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            !brdStatus.regeneration_required &&
            isBRDLoading && (
              <div className="rounded-2xl border border-[#e2e2e2] bg-white p-6">
                <p className="text-base text-[#5e5e5e]">Loading BRD...</p>
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            !brdStatus.regeneration_required &&
            isBRDError && (
              <div className="rounded-2xl border border-[#e2e2e2] bg-white p-6">
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
      </div>

      {isGmailBrowserOpen && (
        <GmailSourceBrowser
          onClose={() => {
            if (!importGmailMutation.isPending) {
              setIsGmailBrowserOpen(false);
            }
          }}
          onImport={handleImportGmailMessages}
          isImporting={importGmailMutation.isPending}
        />
      )}
    </main>
  );
}
