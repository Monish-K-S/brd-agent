import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { deleteDocument, getDocuments, uploadDocuments } from "@/api/documents";
import { getWorkspace } from "@/api/workspaces";

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

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadDocuments(id!, files),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(id!, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", id],
      });
    },
  });

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

        <section className="p-6">
          <h2 className="text-xl font-semibold">BRD</h2>

          <div className="mt-6 rounded-lg border p-8 text-center">
            <p className="text-muted-foreground">No BRD generated yet.</p>
          </div>
        </section>
      </div>
    </main>
  );
}
