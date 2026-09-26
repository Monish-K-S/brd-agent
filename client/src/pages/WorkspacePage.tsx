import { Suspense, lazy, useEffect, useRef, useState } from "react";
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

// Server job phases (processing_sources | preparing_knowledge |
// generating_brd | null while queued) mapped onto the UI step order.
function mapJobPhaseToStep(
  phase: string | null,
): "processing-sources" | "preparing-knowledge" | "generating-brd" {
  switch (phase) {
    case "preparing_knowledge":
      return "preparing-knowledge";
    case "generating_brd":
      return "generating-brd";
    default:
      return "processing-sources";
  }
}

export default function WorkspacePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { id } = useParams();
  const { signOut } = useAuth();

  // Job tracking for async generation (Phase 2b): the job created (or
  // adopted) by this page. Non-null while a run is in flight — drives
  // status polling, the progress card, and reload resume.
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);
  const [generationServerError, setGenerationServerError] = useState<
    string | null
  >(null);

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
    // Poll only while tracking a job; idle pages make zero extra
    // requests. Stops automatically when tracking clears on completion.
    refetchInterval: trackedJobId !== null ? 2000 : false,
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
    // BRD content only changes via generate/edit, both of which invalidate
    // this key — remount refetches within 5 min are pure waste.
    staleTime: 5 * 60_000,
  });

  type GenerationStep =
    "idle" | "processing-sources" | "preparing-knowledge" | "generating-brd";

  const [generationStep, setGenerationStep] = useState<GenerationStep>("idle");

  const [generationError, setGenerationError] = useState(false);
  const [skippedExtraction, setSkippedExtraction] = useState(false);

  // Synchronous double-run guard: ref (not state) so two clicks in the
  // same tick can't both pass the idle check before re-render.
  const generatingRef = useRef(false);
  // Per-step elapsed clock for the progress card. Timestamps are set
  // alongside each step advance; the 1s ticker below re-renders only
  // while generation is in flight.
  const [stepStartedAt, setStepStartedAt] = useState<number | null>(null);
  const [generationNow, setGenerationNow] = useState(0);

  const canGenerateBRD = Boolean(
    brdStatus &&
      ((!brdStatus.has_brd && brdStatus.has_sources) ||
        brdStatus.regeneration_required),
  );

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadDocuments(id!, files),
    onSuccess: () => {
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["documents", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
      ]);

      flashSources("Added");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(id!, documentId),
    onSuccess: () => {
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["documents", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
      ]);

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
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["documents", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
      ]);

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

  function beginStep(step: Exclude<GenerationStep, "idle">) {
    const now = Date.now();
    setStepStartedAt(now);
    setGenerationNow(now);
    setGenerationStep(step);
  }

  function endGeneration() {
    generatingRef.current = false;
    setStepStartedAt(null);
    setGenerationStep("idle");
    setTrackedJobId(null);
  }

  async function finishTrackedJob(
    outcome: "succeeded" | "failed",
    serverError: string | null,
  ) {
    if (outcome === "succeeded") {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd", id],
        }),
      ]);

      endGeneration();
      showGeneratedNote();
    } else {
      endGeneration();
      setGenerationError(true);
      setGenerationServerError(serverError);

      await queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });
    }
  }

  async function handleGenerateBRD() {
    if (
      !id ||
      !canGenerateBRD ||
      generationStep !== "idle" ||
      generatingRef.current
    ) {
      return;
    }

    generatingRef.current = true;

    try {
      setGenerationError(false);
      setGenerationServerError(null);
      setSkippedExtraction(!brdStatus?.has_new_sources);

      // 202: job created (or the already-running job, per the
      // server-side concurrent guard). Work happens in-process; the
      // progress card follows via status polling below.
      const job = await generateBRD(id);

      if (job.status === "succeeded") {
        await finishTrackedJob("succeeded", null);
      } else if (job.status === "failed") {
        await finishTrackedJob("failed", job.error);
      } else {
        setTrackedJobId(job.job_id);
        beginStep(mapJobPhaseToStep(job.phase));
      }
    } catch {
      endGeneration();
      setGenerationError(true);

      await queryClient.invalidateQueries({
        queryKey: ["brd-status", id],
      });
    }
  }

  // Follow the server-reported phase while tracking a job. The local
  // step (and its elapsed stamp) advances only on real phase changes.
  // Updates are deferred to a timer: repo lint forbids synchronous
  // setState in effects; timer callbacks are the accepted pattern
  // (cf. the progress ticker below).
  useEffect(() => {
    if (trackedJobId === null) {
      return;
    }

    const activeJob = brdStatus?.active_job;

    if (activeJob?.job_id !== trackedJobId) {
      return;
    }

    const step = mapJobPhaseToStep(activeJob.phase);

    if (step === generationStep) {
      return;
    }

    const timer = window.setTimeout(() => {
      beginStep(step);
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // beginStep intentionally excluded: stable setState wrappers that
    // would resubscribe pointlessly; phase/step/job drive scheduling.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedJobId, brdStatus?.active_job?.job_id, brdStatus?.active_job?.phase, generationStep]);

  // Completion: the tracked job left the active slot. last_job names
  // the outcome definitively (no flag heuristics).
  useEffect(() => {
    if (trackedJobId === null || id === undefined) {
      return;
    }

    if (brdStatus?.active_job?.job_id === trackedJobId) {
      return;
    }

    const lastJob = brdStatus?.last_job;

    if (lastJob?.job_id !== trackedJobId) {
      return;
    }

    const outcome =
      lastJob.status === "succeeded" || lastJob.status === "failed"
        ? lastJob.status
        : null;

    if (outcome === null) {
      return;
    }

    const serverError = lastJob.error;

    const timer = window.setTimeout(() => {
      void finishTrackedJob(outcome, serverError);
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // finishTrackedJob intentionally excluded: async completion handler;
    // job identity drives scheduling.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedJobId, id, brdStatus?.active_job?.job_id, brdStatus?.last_job]);

  // Reload resume: adopt a server-side active job this page isn't
  // tracking yet, so progress survives a refresh mid-run.
  useEffect(() => {
    const activeJob = brdStatus?.active_job;
    const hasNewSources = brdStatus?.has_new_sources === true;

    if (
      trackedJobId !== null ||
      generationStep !== "idle" ||
      activeJob === undefined ||
      activeJob === null
    ) {
      return;
    }

    const timer = window.setTimeout(() => {
      generatingRef.current = true;
      setGenerationError(false);
      setGenerationServerError(null);
      setSkippedExtraction(!hasNewSources);
      setTrackedJobId(activeJob.job_id);
      beginStep(mapJobPhaseToStep(activeJob.phase));
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
    // beginStep intentionally excluded (see above).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedJobId, generationStep, brdStatus?.active_job?.job_id, brdStatus?.has_new_sources]);

  // 1s ticker driving the per-step elapsed display. Runs only while a
  // generation is in flight; cleanup stops it on idle or unmount.
  useEffect(() => {
    if (generationStep === "idle") {
      return;
    }

    const interval = window.setInterval(() => {
      setGenerationNow(Date.now());
    }, 1000);

    return () => {
      window.clearInterval(interval);
    };
  }, [generationStep]);

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
  const fileInputRef = useRef<HTMLInputElement>(null);

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

    const duplicate = findDuplicateUpload(files);

    if (duplicate) {
      setUploadValidationError(
        `Duplicate file: ${duplicate}. A file with the same name, type, and size already exists in this workspace`,
      );
      return;
    }

    uploadMutation.mutate(files);
  }

  // Hard-block client-side mirror of the server triple check
  // (file name + extension + byte size). The server re-validates.
  function findDuplicateUpload(files: File[]): string | null {
    const seen = new Set<string>();

    for (const file of files) {
      const suffix = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
      const key = `${file.name}|${suffix}|${file.size}`;

      if (seen.has(key)) {
        return file.name;
      }

      seen.add(key);

      const alreadyStored = (documents ?? []).some((document) => {
        const metadata = document.metadata ?? {};

        return (
          metadata.file_name === file.name &&
          metadata.extension === suffix &&
          metadata.size_bytes === file.size
        );
      });

      if (alreadyStored) {
        return file.name;
      }
    }

    return null;
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
      <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
        <div
          aria-label="Loading workspace"
          className="w-full max-w-2xl space-y-4"
        >
          <Skeleton className="h-8 w-2/5" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </main>
    );
  }

  if (isWorkspaceError || !workspace) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-canvas px-4 sm:px-8">
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
        ? "md:grid-cols-[56px_minmax(0,1fr)_320px]"
        : !qaOpen
          ? "md:grid-cols-[300px_minmax(0,1fr)_56px]"
          : "md:grid-cols-[300px_minmax(0,1fr)_320px]";

  // Document measure follows the rails: comfortable at full chrome,
  // roomier as rails collapse. Transition is motion-safe via the global
  // reduced-motion kill-switch.
  const docMeasure =
    !sourcesOpen && !qaOpen
      ? "max-w-[1024px]"
      : !sourcesOpen || !qaOpen
        ? "max-w-[880px]"
        : "max-w-[720px]";

  return (
    <main className="min-h-screen bg-canvas text-ink">
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
                <h1 className="truncate text-base leading-6 font-semibold text-ink">
                  {workspace.name}
                </h1>

                {workspace.description && (
                  <p className="truncate text-xs leading-5 text-steel">
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
        <aside className="border-b border-hairline-soft bg-canvas p-4 print:hidden md:overflow-y-auto md:border-r md:border-b-0">
          {!sourcesOpen ? (
            <button
              type="button"
              onClick={toggleSources}
              aria-label="Show sources"
              title="Show sources"
              className="flex size-9 items-center justify-center rounded-full bg-surface text-ink transition-colors duration-200 hover:bg-black/5"
            >
              <ChevronRight />
            </button>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-ink">
                  Sources
                  {(documents?.length ?? 0) > 0 && (
                    <span className="ml-2 text-sm font-normal text-stone">
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
                  className="flex size-9 items-center justify-center rounded-full text-ink transition-colors duration-200 hover:bg-black/5"
                >
                  <ChevronLeft />
                </button>
              </div>

          <section className="mt-4">
            <div>
              {/* Real button (keyboard-operable) driving the hidden file
                  input — a label pill alone is not focusable. */}
              <Button
                type="button"
                className="w-full"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                <Upload />
                {uploadMutation.isPending ? "Uploading..." : "Add"}
              </Button>

              <input
                ref={fileInputRef}
                id="workspace-sources-upload"
                type="file"
                multiple
                accept=".txt,.pdf,.docx"
                className="sr-only"
                onChange={handleFileChange}
                disabled={uploadMutation.isPending}
                tabIndex={-1}
                aria-hidden="true"
              />
            </div>

            <p className="mt-2 text-xs leading-5 text-stone">
              .txt, .pdf, .docx
            </p>

            {isDocumentsLoading && (
              <div className="mt-4 space-y-2" aria-label="Loading sources">
                {[0, 1].map((index) => (
                  <div
                    key={index}
                    className="rounded-2xl border border-hairline bg-canvas p-4"
                  >
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="mt-2 h-3 w-1/3" />
                  </div>
                ))}
              </div>
            )}

            {isDocumentsError && (
              <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl border border-hairline bg-canvas p-4">
                <p className="text-sm text-ink">
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
                <p className="mt-4 text-sm leading-5 text-steel">
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
                      className="rounded-2xl border border-hairline bg-canvas p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-start gap-3">
                          <span
                            aria-hidden="true"
                            className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface text-ink"
                          >
                            <FileText />
                          </span>

                          <div className="min-w-0">
                            <p
                              className="line-clamp-2 text-sm leading-5 font-medium text-ink"
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
          <section className="mt-8 border-t border-hairline-soft pt-6">
            <h2 className="text-base font-semibold text-ink">Gmail</h2>

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
              <p className="mt-3 text-xs text-steel">Checking...</p>
            )}

            {!isGmailStatusLoading && isGmailStatusError && (
              <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl border border-hairline bg-canvas p-3">
                <p className="text-sm text-ink">
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
                  <p className="mt-3 truncate text-xs text-stone">
                    {gmailStatus.email}
                  </p>

                  {emailDocuments.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {emailDocuments.map((document) => (
                        <div
                          key={document.id}
                          className="rounded-2xl border border-hairline bg-canvas p-4"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex min-w-0 items-start gap-3">
                              <span
                                aria-hidden="true"
                                className="flex size-9 shrink-0 items-center justify-center rounded-full bg-surface text-ink"
                              >
                                <Mail />
                              </span>

                              <div className="min-w-0">
                                <p
                                  className="line-clamp-2 text-sm leading-5 font-medium text-ink"
                                  title={document.title || "No subject"}
                                >
                                  {document.title || "No subject"}
                                </p>

                                {document.author && (
                                  <p
                                    className="mt-1 truncate text-xs text-steel"
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

        <section className="min-h-0 min-w-0 overflow-y-auto bg-surface p-4 print:bg-canvas print:p-0 sm:p-8">
          <div
            className={`mx-auto mb-6 flex w-full ${docMeasure} flex-wrap items-center justify-between gap-3 transition-[max-width] duration-200 print:hidden`}
          >
            <div className="flex items-center gap-3">
              <h2 className="text-2xl leading-[1.3] font-semibold text-ink">BRD</h2>

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
            <div
              className={`mx-auto w-full ${docMeasure} rounded-2xl border border-hairline bg-canvas p-6 transition-[max-width] duration-200 print:hidden`}
            >
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

                  const activeElapsedSeconds =
                    isActive && stepStartedAt !== null
                      ? Math.max(
                          0,
                          Math.round((generationNow - stepStartedAt) / 1000),
                        )
                      : 0;

                  return (
                    <li key={step} className="flex items-center gap-3">
                      {isActive ? (
                        <Loader2
                          aria-hidden="true"
                          className="size-4 animate-spin text-ink"
                        />
                      ) : (
                        <span
                          aria-hidden="true"
                          className={
                            isDone
                              ? "size-2 rounded-full bg-primary"
                              : "size-2 rounded-full border border-ink/20"
                          }
                        />
                      )}

                      <span
                        className={
                          isActive || isDone
                            ? "text-base font-medium text-ink"
                            : "text-base text-steel"
                        }
                      >
                        {label}
                        {isActive ? `... ${activeElapsedSeconds}s` : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>

              <p className="mt-4 text-xs leading-5 text-stone">
                Large workspaces can take a couple of minutes.
              </p>
            </div>
          )}

          {generationStep === "idle" && generationError && (
            <StateAlert className="mb-6 print:hidden">
              Generation failed.{" "}
              {generationServerError ?? "Try again."}
            </StateAlert>
          )}

          {generationStep === "idle" && isBRDStatusLoading && (
            <div
              aria-label="Loading BRD status"
              className={`mx-auto w-full ${docMeasure} space-y-3 rounded-2xl border border-hairline bg-canvas p-6 transition-[max-width] duration-200 print:hidden`}
            >
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-4 w-full" />
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div
              className={`mx-auto flex w-full ${docMeasure} items-center justify-between gap-3 rounded-2xl border border-hairline bg-canvas p-4 transition-[max-width] duration-200 print:hidden`}
            >
              <p className="text-sm text-ink">Something went wrong.</p>

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
                    <Button
                      onClick={handleGenerateBRD}
                      disabled={generationStep !== "idle"}
                    >
                      {generationStep !== "idle" ? "Generating..." : "Generate"}
                    </Button>
                  ) : undefined
                }
                className={`mx-auto w-full ${docMeasure} border border-hairline bg-canvas transition-[max-width] duration-200 print:hidden`}
              />
            )}

          {/* Outdated BRD */}
          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required && (
              <div
                className={`mx-auto mb-6 w-full ${docMeasure} rounded-2xl border border-hairline bg-canvas p-6 transition-[max-width] duration-200 print:hidden`}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-base font-medium text-ink">
                      New sources available.
                    </p>

                    {brdStatus.has_user_edits && (
                      <p className="mt-1 text-sm leading-5 text-steel">
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
              className={`mx-auto w-full ${docMeasure} rounded-2xl border border-hairline bg-canvas p-6 transition-[max-width] duration-200 sm:p-8`}
              aria-label="Loading BRD"
            >
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="mt-4 h-8 w-2/3" />
              <Skeleton className="mt-4 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-5/6" />

              <div className="mt-8 border-t border-hairline-soft pt-8">
                <Skeleton className="h-5 w-1/4" />
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-4/6" />
              </div>
            </div>
          )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDError && (
            <div
              className={`mx-auto flex w-full ${docMeasure} items-center justify-between gap-3 rounded-2xl border border-hairline bg-canvas p-4 transition-[max-width] duration-200 print:hidden`}
            >
              <p className="text-sm text-ink">Something went wrong.</p>

              <Button variant="ghost" size="sm" onClick={() => refetchBRD()}>
                Retry
              </Button>
            </div>
          )}

          {exportFailed && (
            <StateAlert
              className={`mx-auto w-full ${docMeasure} mb-6 transition-[max-width] duration-200 print:hidden`}
            >
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
              <div
                className={`mx-auto w-full ${docMeasure} transition-[max-width] duration-200`}
              >
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
              </div>
            )}
        </section>

        {id &&
          (qaOpen ? (
            <BRDQAPanel workspaceId={id} onCollapse={toggleQa} />
          ) : (
            <div className="border-t border-hairline-soft bg-canvas p-4 print:hidden md:border-t-0 md:border-l">
              <button
                type="button"
                onClick={toggleQa}
                aria-label="Show Q&A"
                title="Show Q&A"
                className="flex size-9 items-center justify-center rounded-full bg-surface text-ink transition-colors duration-200 hover:bg-black/5"
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
