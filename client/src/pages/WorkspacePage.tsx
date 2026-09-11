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
  exportBRDPdf,
  exportBRDDocx,
} from "@/api/brd";
import { consolidateProjectKnowledge } from "@/api/projectKnowledge";
import { extractDocuments } from "@/api/extractions";
import { BRDViewer } from "@/components/brd/BRDViewer";

export default function WorkspacePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const { signOut } = useAuth();

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
    "idle" | "processing-sources" | "preparing-knowledge" | "generating-brd";

  const [generationStep, setGenerationStep] = useState<GenerationStep>("idle");

  const [generationError, setGenerationError] = useState(false);

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
    if (!id || !brdStatus?.has_new_sources) {
      return;
    }

    try {
      setGenerationError(false);

      setGenerationStep("processing-sources");
      await extractDocuments(id);

      setGenerationStep("preparing-knowledge");
      await consolidateProjectKnowledge(id);

      setGenerationStep("generating-brd");
      await generateBRD(id);

      setGenerationStep("idle");

      await queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });

      await queryClient.invalidateQueries({
        queryKey: ["brd", id],
      });
    } catch {
      setGenerationStep("idle");
      setGenerationError(true);
    }
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

  if (isWorkspaceLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading workspace...</p>
      </main>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p className="text-destructive">Failed to load workspace.</p>

        <Button variant="outline" onClick={() => navigate("/workspaces")}>
          Back to Workspaces
        </Button>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/workspaces")}>
            ← Workspaces
          </Button>

          <div>
            <h1 className="text-lg font-semibold">{workspace.name}</h1>

            {workspace.description && (
              <p className="text-sm text-muted-foreground">
                {workspace.description}
              </p>
            )}
          </div>
        </div>

        <Button variant="outline" onClick={handleSignOut}>
          Sign out
        </Button>
      </header>

      <div className="grid min-h-[calc(100vh-81px)] grid-cols-1 md:grid-cols-[280px_1fr]">
        <aside className="border-b p-6 md:border-b-0 md:border-r">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide">
              Sources
            </h2>

            <label className="inline-flex cursor-pointer">
              <span className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90">
                {uploadMutation.isPending ? "Uploading..." : "Add sources"}
              </span>

              <input
                type="file"
                multiple
                accept=".txt,.pdf,.docx"
                className="hidden"
                onChange={handleFileChange}
                disabled={uploadMutation.isPending}
              />
            </label>
          </div>

          {isDocumentsLoading && (
            <p className="mt-4 text-sm text-muted-foreground">
              Loading sources...
            </p>
          )}

          {isDocumentsError && (
            <p className="mt-4 text-sm text-destructive">
              Failed to load sources.
            </p>
          )}

          {!isDocumentsLoading &&
            !isDocumentsError &&
            documents?.length === 0 && (
              <p className="mt-4 text-sm text-muted-foreground">
                No sources yet.
              </p>
            )}

          {!isDocumentsLoading &&
            !isDocumentsError &&
            documents &&
            documents.length > 0 && (
              <div className="mt-4 space-y-2">
                {documents.map((document) => (
                  <div key={document.id} className="rounded-md border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {document.title || "Untitled source"}
                        </p>

                        <p className="mt-1 text-xs text-muted-foreground">
                          {document.source_type}
                        </p>
                      </div>

                      <Button
                        variant="ghost"
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
            <p className="mt-4 text-sm text-destructive" role="alert">
              Failed to upload sources. Please try again.
            </p>
          )}

          {deleteMutation.isError && (
            <p className="mt-4 text-sm text-destructive" role="alert">
              Failed to delete source. Please try again.
            </p>
          )}
        </aside>

        <section className="bg-muted/20 p-6">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-semibold">BRD</h2>

            {brdStatus?.has_brd && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={<Button variant="outline">Download</Button>}
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
            <div className="rounded-lg border bg-background p-8">
              <p className="font-medium">
                {generationStep === "processing-sources" &&
                  "Processing sources..."}

                {generationStep === "preparing-knowledge" &&
                  "Preparing project knowledge..."}

                {generationStep === "generating-brd" && "Generating BRD..."}
              </p>

              <p className="mt-2 text-sm text-muted-foreground">
                This may take a little while.
              </p>
            </div>
          )}

          {generationStep === "idle" && generationError && (
            <div className="mb-6 rounded-lg border border-destructive/30 bg-background p-4">
              <p className="text-sm text-destructive" role="alert">
                Failed to generate BRD. Please try again.
              </p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusLoading && (
            <div className="rounded-lg border bg-background p-8">
              <p className="text-muted-foreground">Checking BRD status...</p>
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div className="rounded-lg border bg-background p-8">
              <p className="text-destructive">Failed to load BRD status.</p>
            </div>
          )}

          {generationStep === "idle" &&
            !isBRDStatusLoading &&
            !isBRDStatusError &&
            brdStatus &&
            !brdStatus.has_brd && (
              <div className="rounded-lg border bg-background p-8">
                <p className="text-muted-foreground">No BRD generated yet.</p>

                {brdStatus.has_new_sources && (
                  <>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Sources are ready for BRD generation.
                    </p>

                    <Button className="mt-4" onClick={handleGenerateBRD}>
                      Generate BRD
                    </Button>
                  </>
                )}
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required && (
              <div className="mb-6 rounded-lg border bg-background p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium">BRD needs to be regenerated.</p>

                    <p className="mt-1 text-sm text-muted-foreground">
                      New sources have been added since the last BRD generation.
                    </p>
                  </div>

                  <Button onClick={handleGenerateBRD}>Regenerate BRD</Button>
                </div>
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            !brdStatus.regeneration_required &&
            isBRDLoading && (
              <div className="rounded-lg border bg-background p-8">
                <p className="text-muted-foreground">Loading BRD...</p>
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            !brdStatus.regeneration_required &&
            isBRDError && (
              <div className="rounded-lg border bg-background p-8">
                <p className="text-destructive">Failed to load BRD.</p>
              </div>
            )}

          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brd &&
            !isBRDError && <BRDViewer data={brd.brd_data} />}
        </section>
      </div>
    </main>
  );
}
