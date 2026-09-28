import { memo, useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/useAuth";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createWorkspace,
  deleteWorkspace,
  getWorkspace,
  getWorkspaces,
  type Workspace,
} from "@/api/workspaces";
import { getBRDStatus } from "@/api/brd";
import { TopBar } from "@/components/layout/TopBar";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, Eyebrow, StateAlert } from "@/components/ui/status";

function formatUpdatedAt(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function mutationDetail(error: unknown): string | null {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: unknown }).response;

    if (typeof response === "object" && response !== null && "data" in response) {
      const detail = (response as { data?: unknown }).data;

      if (
        typeof detail === "object" &&
        detail !== null &&
        "detail" in detail &&
        typeof (detail as { detail?: unknown }).detail === "string"
      ) {
        return (detail as { detail: string }).detail;
      }
    }
  }

  return null;
}

type WorkspaceCardProps = {
  workspace: Workspace;
  onOpen: (id: string) => void;
  onAskDelete: (id: string) => void;
  onPrefetch: (id: string) => void;
};

// Memoized so keystrokes in search, dialog open/close, and other cards'
// pending states don't re-render every card — element refs from the query
// cache are stable, so unchanged cards bail out.
const WorkspaceCard = memo(function WorkspaceCard({
  workspace,
  onOpen,
  onAskDelete,
  onPrefetch,
}: WorkspaceCardProps) {
  const updatedAt = formatUpdatedAt(workspace.updated_at);

  return (
    <div
      className="flex flex-col rounded-2xl border border-hairline bg-canvas p-6 transition-all duration-200 hover:border-brand-coral/40 hover:shadow-level-1"
    >
      <button
        type="button"
        onClick={() => onOpen(workspace.id)}
        onMouseEnter={() => onPrefetch(workspace.id)}
        onFocus={() => onPrefetch(workspace.id)}
        className="w-full flex-1 text-left"
      >
        <h2 className="text-xl leading-7 font-semibold text-ink">
          {workspace.name}
        </h2>

        {workspace.description && (
          <p className="mt-1 line-clamp-2 text-sm leading-6 text-steel">
            {workspace.description}
          </p>
        )}

        {updatedAt && (
          <p className="mt-4 text-xs leading-5 text-steel">
            Updated {updatedAt}
          </p>
        )}
      </button>

      <div className="mt-2 flex justify-end">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onAskDelete(workspace.id)}
        >
          Delete
        </Button>
      </div>
    </div>
  );
});

export default function WorkspacesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"recent" | "az">("recent");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const {
    data: workspaces,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["workspaces"],
    queryFn: getWorkspaces,
    // List only changes via create/delete, both of which invalidate.
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: createWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["workspaces"],
      });

      setName("");
      setDescription("");
      setDialogOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["workspaces"],
      });

      setPendingDeleteId(null);
    },
  });

  async function handleSignOut() {
    await signOut();
    navigate("/auth", { replace: true });
  }

  function handleCreateWorkspace(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();
    const trimmedDescription = description.trim();

    if (!trimmedName || isDuplicateName(trimmedName)) {
      return;
    }

    createMutation.mutate({
      name: trimmedName,
      description: trimmedDescription || undefined,
    });
  }

  function isDuplicateName(trimmedName: string): boolean {
    return (workspaces ?? []).some(
      (workspace) =>
        workspace.name.toLowerCase() === trimmedName.toLowerCase(),
    );
  }

  const duplicateNameEntered =
    name.trim().length > 0 && isDuplicateName(name.trim());

  function handleConfirmDelete() {
    if (!pendingDeleteId || deleteMutation.isPending) {
      return;
    }

    deleteMutation.mutate(pendingDeleteId);
  }

  const trimmedSearch = search.trim().toLowerCase();
  const visibleWorkspaces = useMemo(
    () =>
      (workspaces ?? [])
        .filter((workspace) => {
          if (!trimmedSearch) {
            return true;
          }

          return (
            workspace.name.toLowerCase().includes(trimmedSearch) ||
            (workspace.description ?? "")
              .toLowerCase()
              .includes(trimmedSearch)
          );
        })
        .sort((a, b) => {
          if (sort === "az") {
            return a.name.localeCompare(b.name);
          }

          const aTime = new Date(a.updated_at).getTime();
          const bTime = new Date(b.updated_at).getTime();

          if (Number.isNaN(aTime) || Number.isNaN(bTime)) {
            return 0;
          }

          return bTime - aTime;
        }),
    [workspaces, trimmedSearch, sort],
  );

  const countText = useMemo(() => {
    const totalCount = (workspaces ?? []).length;
    const latestUpdated = (workspaces ?? [])
      .map((workspace) => new Date(workspace.updated_at).getTime())
      .filter((time) => !Number.isNaN(time));
    const latestUpdatedText =
      latestUpdated.length > 0
        ? formatUpdatedAt(new Date(Math.max(...latestUpdated)).toISOString())
        : "";

    return totalCount === 0
      ? ""
      : `${totalCount} project${totalCount === 1 ? "" : "s"}${
          latestUpdatedText ? ` · Updated ${latestUpdatedText}` : ""
        }`;
  }, [workspaces]);

  const handleOpenWorkspace = useCallback(
    (workspaceId: string) => {
      navigate(`/workspaces/${workspaceId}`);
    },
    [navigate],
  );

  const handleAskDelete = useCallback((workspaceId: string) => {
    setPendingDeleteId(workspaceId);
  }, []);

  // Warm the detail-page queries on hover/focus so open feels instant.
  // Only workspace + brd-status: ["brd", id] is enabled solely when
  // brdStatus.has_brd, so prefetching it blind could 404. staleTime on
  // the detail queries makes repeat hovers free.
  const handlePrefetchWorkspace = useCallback(
    (workspaceId: string) => {
      void queryClient.prefetchQuery({
        queryKey: ["workspace", workspaceId],
        queryFn: () => getWorkspace(workspaceId),
      });
      void queryClient.prefetchQuery({
        queryKey: ["brd-status", workspaceId],
        queryFn: () => getBRDStatus(workspaceId),
      });
    },
    [queryClient],
  );

  const pendingDeleteWorkspace = (workspaces ?? []).find(
    (workspace) => workspace.id === pendingDeleteId,
  );

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <TopBar
        left={
          <span className="text-base font-semibold text-ink">BRD Agent</span>
        }
        right={
          <Button variant="subtle" size="sm" onClick={handleSignOut}>
            Sign out
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-[1280px] px-4 pt-8 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Eyebrow dot>Your projects</Eyebrow>
            <h1 className="mt-1 text-h1 leading-[1.2] font-semibold tracking-[-1px] text-ink">
              Workspaces
            </h1>

            {!isLoading && !isError && countText && (
              <p className="mt-2 text-base text-steel">{countText}</p>
            )}
          </div>

          <Button onClick={() => setDialogOpen(true)}>New workspace</Button>
        </div>

        {(workspaces ?? []).length > 0 && (
          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search"
              aria-label="Search workspaces"
              className="h-9 w-full max-w-xs rounded-lg border border-hairline bg-surface px-4 text-sm text-ink outline-none placeholder:text-steel focus-visible:border-ink"
            />

            <div
              role="group"
              aria-label="Sort workspaces"
              className="flex items-center gap-2"
            >
              {(
                [
                  { value: "recent", label: "Recent" },
                  { value: "az", label: "A–Z" },
                ] as const
              ).map((option) => (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={sort === option.value}
                  onClick={() => setSort(option.value)}
                  className={
                    sort === option.value
                      ? "inline-flex min-h-9 items-center rounded-full border border-primary bg-primary px-4 text-sm font-medium text-white transition-colors duration-200"
                      : "inline-flex min-h-9 items-center rounded-full border border-hairline bg-canvas px-4 text-sm font-medium text-steel transition-colors duration-200 hover:text-ink"
                  }
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 bg-surface">
        <div className="mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-8">
          <section aria-label="Workspaces">
          {isLoading && (
            <div
              className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
              aria-label="Loading workspaces"
            >
              {[0, 1, 2].map((index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-hairline bg-canvas p-6"
                >
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="mt-3 h-4 w-full" />
                  <Skeleton className="mt-2 h-4 w-1/2" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <div className="flex items-center justify-between gap-3 rounded-2xl border border-hairline bg-canvas p-4">
              <p className="text-sm text-ink">Something went wrong.</p>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => refetch()}
              >
                Retry
              </Button>
            </div>
          )}

          {!isLoading && !isError && workspaces?.length === 0 && (
            <EmptyState
              title="Create your first workspace"
              description="Add project files and generate a BRD from them."
              className="border border-hairline bg-canvas"
              action={
                <Button onClick={() => setDialogOpen(true)}>
                  New workspace
                </Button>
              }
            />
          )}

          {!isLoading &&
            !isError &&
            workspaces &&
            workspaces.length > 0 &&
            visibleWorkspaces.length === 0 && (
              <p className="rounded-2xl border border-hairline bg-canvas p-6 text-center text-base text-steel">
                No matches.
              </p>
            )}

          {!isLoading && !isError && visibleWorkspaces.length > 0 && (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              <button
                type="button"
                onClick={() => setDialogOpen(true)}
                className="group flex min-h-[180px] flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-hairline bg-canvas p-6 text-steel transition-colors duration-200 hover:border-brand-coral hover:text-ink"
              >
                <Plus aria-hidden="true" className="size-5 transition-colors duration-200 group-hover:text-brand-coral" />
                <span className="text-base font-medium">New workspace</span>
              </button>

              {visibleWorkspaces.map((workspace) => (
                <WorkspaceCard
                  key={workspace.id}
                  workspace={workspace}
                  onOpen={handleOpenWorkspace}
                  onAskDelete={handleAskDelete}
                  onPrefetch={handlePrefetchWorkspace}
                />
              ))}
            </div>
          )}
          </section>
        </div>
      </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogContent>
            <form onSubmit={handleCreateWorkspace}>
              <DialogHeader>
                <DialogTitle>New workspace</DialogTitle>

                <DialogDescription>
                  Name the project you want a BRD for.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="workspace-name">Name</Label>

                  <Input
                    id="workspace-name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="My project"
                    autoFocus
                  />

                  {duplicateNameEntered && (
                    <p className="text-sm text-ink" role="alert">
                      A workspace with this name already exists.
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="workspace-description">Description</Label>

                  <Input
                    id="workspace-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Optional"
                  />
                </div>

                {createMutation.isError && (
                  <StateAlert>
                    {mutationDetail(createMutation.error) ??
                      "Couldn't create it. Please try again."}
                  </StateAlert>
                )}

                {deleteMutation.isError && (
                  <StateAlert>
                    Couldn&apos;t delete it. Please try again.
                  </StateAlert>
                )}
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="subtle"
                  onClick={() => setDialogOpen(false)}
                  disabled={createMutation.isPending}
                >
                  Cancel
                </Button>

                <Button
                  type="submit"
                  disabled={
                    !name.trim() ||
                    duplicateNameEntered ||
                    createMutation.isPending
                  }
                >
                  {createMutation.isPending ? "Creating..." : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        <Dialog
          open={pendingDeleteId !== null}
          onOpenChange={(open) => {
            if (!open && !deleteMutation.isPending) {
              setPendingDeleteId(null);
            }
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete this workspace?</DialogTitle>

              <DialogDescription>
                {pendingDeleteWorkspace
                  ? `“${pendingDeleteWorkspace.name}” and everything in it will be removed. `
                  : ""}
                This can&apos;t be undone.
              </DialogDescription>
            </DialogHeader>

            {deleteMutation.isError && (
              <StateAlert>
                Couldn&apos;t delete it. Please try again.
              </StateAlert>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="subtle"
                onClick={() => setPendingDeleteId(null)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </Button>

              <Button
                type="button"
                variant="destructive"
                onClick={handleConfirmDelete}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
    </main>
  );
}
