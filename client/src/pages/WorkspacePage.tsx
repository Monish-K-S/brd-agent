import { Suspense, lazy, useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useAuth } from "@/auth/useAuth";
import NotFoundPage, { ErrorHero } from "@/pages/NotFoundPage";
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
  connectDrive,
  disconnectDrive,
  getDrivePickerToken,
  getDriveStatus,
  importDriveFiles,
} from "@/api/drive";
import {
  loadGooglePicker,
  openDrivePicker,
} from "@/components/drive/drivePicker";
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
import { FieldBackdrop } from "@/components/brand/FieldBackdrop";
import { Skeleton } from "@/components/ui/skeleton";
import {
  EmptyState,
  Eyebrow,
  FlashNote,
  StateAlert,
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

// Compact source index row shared by the uploads, Gmail, and Drive
// lists: single-line title plus a one-line meta row (neutral type badge
// + optional subtitle). Rows sit in hairline-divided groups so long
// source lists stay scannable without card chrome.
function SourceCard({
  icon,
  title,
  badge,
  subtitle,
  documentId,
  isDeleting,
  onDelete,
}: {
  icon: ReactNode;
  title: string;
  badge: string;
  subtitle?: string | null;
  documentId: string;
  isDeleting: boolean;
  onDelete: (documentId: string) => void;
}) {
  return (
    <div className="group/source -mx-2 flex items-center justify-between gap-2 rounded-md px-2 py-2.5 transition-colors duration-200 hover:bg-soft/70">
      <div className="flex min-w-0 items-center gap-2.5">
        <span
          aria-hidden="true"
          className="flex size-5 shrink-0 items-center justify-center text-stone"
        >
          {icon}
        </span>

        <div className="min-w-0">
          <p
            className="truncate text-sm leading-5 font-medium text-ink"
            title={title}
          >
            {title}
          </p>

          <p className="mt-0.5 flex min-w-0 items-center gap-1.5">
            <span className="shrink-0 text-xs font-medium text-steel">
              {badge}
            </span>

            {subtitle && (
              <span className="truncate text-xs text-steel" title={subtitle}>
                {subtitle}
              </span>
            )}
          </p>
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Delete source"
        title="Delete source"
        className="text-stone opacity-0 transition-opacity duration-200 group-focus-within/source:opacity-100 group-hover/source:opacity-100 hover:text-error"
        onClick={() => onDelete(documentId)}
        disabled={isDeleting}
      >
        <Trash2 />
      </Button>
    </div>
  );
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
  const [isDrivePickerBusy, setIsDrivePickerBusy] = useState(false);
  const [drivePickerError, setDrivePickerError] = useState<string | null>(null);
  const [confirmDisconnectDriveOpen, setConfirmDisconnectDriveOpen] =
    useState(false);

  const {
    data: workspace,
    isLoading: isWorkspaceLoading,
    isError: isWorkspaceError,
    error: workspaceError,
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
    data: driveStatus,
    isLoading: isDriveStatusLoading,
    isError: isDriveStatusError,
    refetch: refetchDriveStatus,
  } = useQuery({
    queryKey: ["drive-status"],
    queryFn: getDriveStatus,
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

  const connectDriveMutation = useMutation({
    mutationFn: () => connectDrive(id!),
    onSuccess: (authorizationUrl) => {
      window.location.assign(authorizationUrl);
    },
  });

  const disconnectDriveMutation = useMutation({
    mutationFn: disconnectDrive,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["drive-status"],
      });
    },
  });

  const importDriveMutation = useMutation({
    mutationFn: (driveFileIds: string[]) =>
      importDriveFiles(id!, driveFileIds),
    onSuccess: (result) => {
      void Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["documents", id],
        }),
        queryClient.invalidateQueries({
          queryKey: ["brd-status", id],
        }),
      ]);

      if (result.imported.length === 0) {
        flashSources("Already added");
      } else if (result.imported.length === 1) {
        flashSources("Added");
      } else {
        flashSources(`Added ${result.imported.length} files`);
      }
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

  function handleConnectDrive() {
    connectDriveMutation.mutate();
  }

  function handleDisconnectDrive() {
    setConfirmDisconnectDriveOpen(true);
  }

  function handleConfirmDisconnectDrive() {
    if (disconnectDriveMutation.isPending) {
      return;
    }

    disconnectDriveMutation.mutate();
    setConfirmDisconnectDriveOpen(false);
  }

  async function handleChooseFromDrive() {
    if (!id || isDrivePickerBusy || importDriveMutation.isPending) {
      return;
    }

    setDrivePickerError(null);
    setIsDrivePickerBusy(true);

    try {
      const accessToken = await getDrivePickerToken();

      await loadGooglePicker();

      openDrivePicker({
        accessToken,
        onPicked: (results) => {
          setIsDrivePickerBusy(false);
          importDriveMutation.mutate(
            results.map((result) => result.driveFileId),
          );
        },
        onCancel: () => {
          setIsDrivePickerBusy(false);
        },
      });
    } catch {
      setIsDrivePickerBusy(false);
      setDrivePickerError("Couldn't open Google Drive. Try again.");
    }
  }

  function driveImportErrorMessage(): string | null {
    if (!importDriveMutation.isError) {
      return null;
    }

    const error = importDriveMutation.error;

    if (isAxiosError(error)) {
      const detail = (
        error.response?.data as { detail?: unknown } | undefined
      )?.detail;

      if (typeof detail === "string" && detail) {
        return detail;
      }
    }

    return "Import failed. Try again.";
  }

  const uploadedDocuments =
    documents?.filter(
      (document) =>
        document.source_type !== "email" &&
        typeof document.metadata.drive_file_id !== "string",
    ) ?? [];

  const emailDocuments =
    documents?.filter((document) => document.source_type === "email") ?? [];

  const driveDocuments =
    documents?.filter(
      (document) => typeof document.metadata.drive_file_id === "string",
    ) ?? [];

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
    // Unknown workspace id (or deleted workspace): render the same
    // themed 404 page as unknown routes. It already routes signed-in
    // users back to /workspaces. Other failures keep retry UI.
    const isNotFound =
      !isWorkspaceError ||
      (isAxiosError(workspaceError) &&
        workspaceError.response?.status === 404);

    if (isNotFound) {
      return (
        <NotFoundPage
          title="This workspace doesn't exist."
          body="It may have been deleted, or the link you followed is wrong."
        />
      );
    }

    return (
      <main className="flex min-h-screen flex-col bg-canvas text-ink">
        <section className="flex flex-1 items-center px-4 py-24 sm:px-8">
          <ErrorHero
            overline="Error"
            title="Something went wrong."
            body="Please try again."
          >
            <Button onClick={() => refetchWorkspace()}>Retry</Button>

            <Button variant="outline" onClick={() => navigate("/workspaces")}>
              Back to Workspaces
            </Button>
          </ErrorHero>
        </section>
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
    <main className="relative min-h-screen print:bg-white">
      <div className="print:hidden">
        <FieldBackdrop intensity="restrained" />
      </div>

      <div className="print:hidden">
        <TopBar
          contained={false}
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
                <p className="text-xs leading-4 font-medium text-steel">
                  Project
                </p>
                <h1 className="truncate text-base leading-6 font-medium text-ink">
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
        className={`shell-cols grid min-h-[calc(100vh-var(--shell-chrome))] grid-cols-1 md:h-[calc(100vh-var(--shell-chrome))] md:overflow-hidden ${gridCols}`}
      >
        <aside className="order-2 border-b border-hairline bg-surface px-4 py-5 print:hidden md:order-none md:overflow-y-auto md:border-r md:border-b-0">
          {!sourcesOpen ? (
            <button
              type="button"
              onClick={toggleSources}
              aria-label="Show sources"
              title="Show sources"
              className="flex size-9 items-center justify-center rounded-full border border-hairline bg-surface text-ink transition-colors duration-200 max-md:size-11 hover:bg-soft"
            >
              <ChevronRight />
            </button>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <h2 className="flex items-baseline gap-2 text-sm font-medium text-ink">
                  Sources
                  {(documents?.length ?? 0) > 0 && (
                    <span className="text-sm text-steel tabular-nums">
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
                  className="flex size-9 items-center justify-center rounded-full text-stone transition-colors duration-200 max-md:size-11 hover:bg-soft hover:text-ink"
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
                variant="default"
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

            <p className="mt-2 text-xs leading-5 text-steel">
              .txt, .pdf, .docx
            </p>

            {isDocumentsLoading && (
              <div className="mt-4 space-y-2 border-t border-hairline pt-4" aria-label="Loading sources">
                {[0, 1].map((index) => (
                  <div key={index} className="py-2.5">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="mt-2 h-3 w-1/3" />
                  </div>
                ))}
              </div>
            )}

            {isDocumentsError && (
              <div className="mt-4 flex items-center justify-between gap-3 border-y border-hairline py-3">
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
              emailDocuments.length === 0 &&
              driveDocuments.length === 0 && (
                <p className="mt-5 border-t border-hairline pt-4 text-sm leading-5 text-steel">
                  Nothing here yet.
                </p>
              )}

            {!isDocumentsLoading &&
              !isDocumentsError &&
              uploadedDocuments.length > 0 && (
                <>
                  <p className="mt-5 flex items-baseline gap-2 text-sm font-medium text-ink">
                    Files
                    <span className="text-xs text-steel tabular-nums">
                      {uploadedDocuments.length}
                    </span>
                  </p>

                  <div className="mt-1 divide-y divide-hairline border-t border-hairline">
                    {uploadedDocuments.map((document) => (
                      <SourceCard
                        key={document.id}
                        icon={<FileText size={16} />}
                        title={document.title || "Untitled source"}
                        badge={document.source_type}
                        documentId={document.id}
                        isDeleting={
                          deleteMutation.isPending &&
                          deleteMutation.variables === document.id
                        }
                        onDelete={handleDeleteDocument}
                      />
                    ))}
                  </div>
                </>
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
          <section className="mt-8 border-t border-hairline pt-5">
            <h2 className="flex items-baseline gap-2 text-sm font-medium text-ink">
              Gmail
              {emailDocuments.length > 0 && (
                <span className="text-xs text-steel tabular-nums">
                  {emailDocuments.length}
                </span>
              )}
            </h2>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {!isGmailStatusLoading &&
                !isGmailStatusError &&
                !gmailStatus?.connected && (
                  <Button
                    variant="outline"
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
                      variant="outline"
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
              <div className="mt-3 flex items-center justify-between gap-3 border-y border-hairline py-3">
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
                  <p className="mt-3 truncate text-xs text-steel">
                    {gmailStatus.email}
                  </p>

                  {emailDocuments.length > 0 && (
                    <div className="mt-1 divide-y divide-hairline border-t border-hairline">
                      {emailDocuments.map((document) => (
                        <SourceCard
                          key={document.id}
                          icon={<Mail size={16} />}
                          title={document.title || "No subject"}
                          badge={document.source_type}
                          subtitle={document.author}
                          documentId={document.id}
                          isDeleting={
                            deleteMutation.isPending &&
                            deleteMutation.variables === document.id
                          }
                          onDelete={handleDeleteDocument}
                        />
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

          {/* Google Drive */}
          <section className="mt-8 border-t border-hairline pt-5">
            <h2 className="flex items-baseline gap-2 text-sm font-medium text-ink">
              Google Drive
              {driveDocuments.length > 0 && (
                <span className="text-xs text-steel tabular-nums">
                  {driveDocuments.length}
                </span>
              )}
            </h2>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {!isDriveStatusLoading &&
                !isDriveStatusError &&
                !driveStatus?.connected && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleConnectDrive}
                    disabled={connectDriveMutation.isPending}
                  >
                    {connectDriveMutation.isPending
                      ? "Connecting..."
                      : "Connect"}
                  </Button>
                )}

              {!isDriveStatusLoading &&
                !isDriveStatusError &&
                driveStatus?.connected && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleChooseFromDrive()}
                      disabled={
                        isDrivePickerBusy || importDriveMutation.isPending
                      }
                    >
                      {importDriveMutation.isPending
                        ? "Importing..."
                        : isDrivePickerBusy
                          ? "Opening..."
                          : "Choose files"}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDisconnectDrive}
                      disabled={disconnectDriveMutation.isPending}
                    >
                      {disconnectDriveMutation.isPending
                        ? "Disconnecting..."
                        : "Disconnect"}
                    </Button>
                  </>
                )}
            </div>

            {isDriveStatusLoading && (
              <p className="mt-3 text-xs text-steel">Checking...</p>
            )}

            {!isDriveStatusLoading && isDriveStatusError && (
              <div className="mt-3 flex items-center justify-between gap-3 border-y border-hairline py-3">
                <p className="text-sm text-ink">
                  Couldn&apos;t check Google Drive.
                </p>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchDriveStatus()}
                >
                  Retry
                </Button>
              </div>
            )}

            {!isDriveStatusLoading &&
              !isDriveStatusError &&
              driveStatus?.connected && (
                <>
                  <p className="mt-3 truncate text-xs text-steel">
                    {driveStatus.email}
                  </p>

                  {driveDocuments.length > 0 && (
                    <div className="mt-1 divide-y divide-hairline border-t border-hairline">
                      {driveDocuments.map((document) => (
                        <SourceCard
                          key={document.id}
                          icon={<FileText size={16} />}
                          title={document.title || "Untitled source"}
                          badge={document.source_type}
                          subtitle={document.author}
                          documentId={document.id}
                          isDeleting={
                            deleteMutation.isPending &&
                            deleteMutation.variables === document.id
                          }
                          onDelete={handleDeleteDocument}
                        />
                      ))}
                    </div>
                  )}
                </>
              )}

            {connectDriveMutation.isError && (
              <StateAlert className="mt-3">
                Connection failed. Try again.
              </StateAlert>
            )}

            {disconnectDriveMutation.isError && (
              <StateAlert className="mt-3">
                Couldn&apos;t disconnect.
              </StateAlert>
            )}

            {drivePickerError && (
              <StateAlert className="mt-3">{drivePickerError}</StateAlert>
            )}

            {driveImportErrorMessage() && (
              <StateAlert className="mt-3">
                {driveImportErrorMessage()}
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

        <section className="order-1 min-h-0 min-w-0 overflow-y-auto px-4 pb-8 pt-0 print:bg-white print:p-0 sm:px-8 md:order-none">
          <div
            className="sticky top-0 z-[5] -mx-4 border-b border-hairline bg-canvas px-4 pb-4 pt-6 print:hidden sm:-mx-8 sm:px-8"
          >
            <div
              className={`mx-auto flex w-full ${docMeasure} flex-wrap items-center justify-between gap-3 transition-[max-width] duration-200`}
            >
            <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
              <p className="truncate text-base leading-6 font-medium text-ink">
                {workspace.name}
              </p>

              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-steel">
                {brdStateLabel && (
                  <span className="flex items-center gap-1.5 text-xs font-medium text-steel">
                    <span
                      aria-hidden="true"
                      className={
                        generationStep !== "idle"
                          ? "size-1.5 animate-pulse rounded-full bg-signal"
                          : brdStatus?.regeneration_required
                            ? "size-1.5 rounded-full bg-warning"
                            : "size-1.5 rounded-full bg-ink"
                      }
                    />
                    {brdStateLabel}
                  </span>
                )}

                {(documents?.length ?? 0) > 0 && (
                  <span className="text-xs text-steel">
                    From {documents?.length}{" "}
                    {documents?.length === 1 ? "source" : "sources"}
                  </span>
                )}
              </p>
            </div>

            {brdStatus?.has_brd && (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button variant="outline">
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
          </div>

          {generationStep !== "idle" && (
            <div
              className={`mx-auto w-full ${docMeasure} border-y border-hairline bg-surface px-5 py-4 transition-[max-width] duration-200 print:hidden`}
            >
              <ol className="space-y-2.5">
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
                          className="size-4 animate-spin text-signal"
                        />
                      ) : (
                        <span
                          aria-hidden="true"
                          className={
                            isDone
                              ? "size-2 rounded-full bg-ink"
                              : "size-2 rounded-full border border-ink/20"
                          }
                        />
                      )}

                      <span
                        className={
                          isActive || isDone
                            ? "text-sm font-medium text-ink"
                            : "text-sm text-steel"
                        }
                      >
                        {label}
                        {isActive ? ` ··· ${activeElapsedSeconds}s` : ""}
                      </span>
                    </li>
                  );
                })}
              </ol>

              <p className="mt-4 text-xs leading-5 text-steel">
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
              className={`mx-auto w-full ${docMeasure} space-y-3 border-y border-hairline bg-surface px-5 py-5 transition-[max-width] duration-200 print:hidden`}
            >
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-4 w-full" />
            </div>
          )}

          {generationStep === "idle" && isBRDStatusError && (
            <div
              className={`mx-auto flex w-full ${docMeasure} items-center justify-between gap-3 border-y border-hairline bg-surface px-5 py-4 transition-[max-width] duration-200 print:hidden`}
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
                      variant="accent"
                      onClick={handleGenerateBRD}
                      disabled={generationStep !== "idle"}
                    >
                      {generationStep !== "idle" ? "Generating..." : "Generate"}
                    </Button>
                  ) : undefined
                }
                className={`mx-auto w-full ${docMeasure} border border-hairline bg-surface transition-[max-width] duration-200 print:hidden`}
              />
            )}

          {/* Outdated BRD */}
          {generationStep === "idle" &&
            brdStatus?.has_brd &&
            brdStatus.regeneration_required && (
              <div
                className={`mx-auto mb-8 w-full ${docMeasure} border border-hairline border-l-2 border-l-signal bg-surface px-5 py-4 transition-[max-width] duration-200 print:hidden`}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <Eyebrow className="text-signal-text">Needs attention</Eyebrow>
                    <p className="mt-1 text-base font-medium text-ink">
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
                    variant="accent"
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
              className={`mx-auto w-full ${docMeasure} bg-surface px-8 py-10 shadow-paper transition-[max-width] duration-200 sm:px-12 sm:py-14`}
              aria-label="Loading BRD"
            >
              <Skeleton className="h-3 w-1/3" />
              <Skeleton className="mt-4 h-9 w-2/3" />
              <Skeleton className="mt-5 h-4 w-full" />
              <Skeleton className="mt-2 h-4 w-5/6" />

              <div className="mt-10 border-t border-hairline pt-8">
                <Skeleton className="h-5 w-1/4" />
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-4/6" />
              </div>
            </div>
          )}

          {generationStep === "idle" && brdStatus?.has_brd && isBRDError && (
            <div
              className={`mx-auto flex w-full ${docMeasure} items-center justify-between gap-3 border-y border-hairline bg-surface px-5 py-4 transition-[max-width] duration-200 print:hidden`}
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
            <div className="order-3 border-t border-hairline bg-surface p-4 print:hidden md:order-none md:border-t-0 md:border-l">
              <button
                type="button"
                onClick={toggleQa}
                aria-label="Show Q&A"
                title="Show Q&A"
                className="flex size-9 items-center justify-center rounded-full border border-hairline bg-surface text-ink transition-colors duration-200 max-md:size-11 hover:bg-soft"
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

      <Dialog
        open={confirmDisconnectDriveOpen}
        onOpenChange={setConfirmDisconnectDriveOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Google Drive?</DialogTitle>

            <DialogDescription>
              Imported files stay. This can&apos;t be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              type="button"
              variant="subtle"
              onClick={() => setConfirmDisconnectDriveOpen(false)}
              disabled={disconnectDriveMutation.isPending}
            >
              Cancel
            </Button>

            <Button
              type="button"
              variant="destructive"
              onClick={handleConfirmDisconnectDrive}
              disabled={disconnectDriveMutation.isPending}
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
