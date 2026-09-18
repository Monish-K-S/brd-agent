import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthProvider";
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
import { createWorkspace, deleteWorkspace, getWorkspaces } from "@/api/workspaces";
import { TopBar } from "@/components/layout/TopBar";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, StateAlert } from "@/components/ui/status";

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

export default function WorkspacesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [search, setSearch] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const {
    data: workspaces,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["workspaces"],
    queryFn: getWorkspaces,
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

    if (!trimmedName) {
      return;
    }

    createMutation.mutate({
      name: trimmedName,
      description: trimmedDescription || undefined,
    });
  }

  function handleConfirmDelete() {
    if (!pendingDeleteId || deleteMutation.isPending) {
      return;
    }

    deleteMutation.mutate(pendingDeleteId);
  }

  const trimmedSearch = search.trim().toLowerCase();
  const visibleWorkspaces = (workspaces ?? []).filter((workspace) => {
    if (!trimmedSearch) {
      return true;
    }

    return (
      workspace.name.toLowerCase().includes(trimmedSearch) ||
      (workspace.description ?? "").toLowerCase().includes(trimmedSearch)
    );
  });

  const pendingDeleteWorkspace = (workspaces ?? []).find(
    (workspace) => workspace.id === pendingDeleteId,
  );

  return (
    <main className="min-h-screen bg-white text-black">
      <TopBar
        left={
          <span className="text-base font-medium text-black">BRD Agent</span>
        }
        right={
          <Button variant="subtle" size="sm" onClick={handleSignOut}>
            Sign out
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-[1200px] px-4 py-8 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-4xl leading-[44px] font-bold text-black">
            Workspaces
          </h1>

          <Button onClick={() => setDialogOpen(true)}>New workspace</Button>
        </div>

        {(workspaces ?? []).length > 0 && (
          <div className="mt-6">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search"
              aria-label="Search workspaces"
              className="h-11 w-full max-w-xs rounded-lg bg-[#efefef] px-4 text-base text-black outline-none placeholder:text-[#afafaf] focus:bg-[#e2e2e2]"
            />
          </div>
        )}

        <section className="mt-6">
          {isLoading && (
            <div
              className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
              aria-label="Loading workspaces"
            >
              {[0, 1, 2].map((index) => (
                <div key={index} className="rounded-2xl bg-[#efefef] p-6">
                  <Skeleton className="h-5 w-2/3" />
                  <Skeleton className="mt-3 h-4 w-full" />
                  <Skeleton className="mt-2 h-4 w-1/2" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-4">
              <p className="text-sm text-black">Something went wrong.</p>

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
              <p className="rounded-2xl bg-[#efefef] p-6 text-center text-base text-[#5e5e5e]">
                No matches.
              </p>
            )}

          {!isLoading && !isError && visibleWorkspaces.length > 0 && (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {visibleWorkspaces.map((workspace) => {
                const updatedAt = formatUpdatedAt(workspace.updated_at);

                return (
                  <div
                    key={workspace.id}
                    className="flex flex-col rounded-2xl bg-[#efefef] p-6"
                  >
                    <button
                      type="button"
                      onClick={() => navigate(`/workspaces/${workspace.id}`)}
                      className="w-full flex-1 text-left"
                    >
                      <h2 className="text-xl leading-7 font-bold text-black">
                        {workspace.name}
                      </h2>

                      {workspace.description && (
                        <p className="mt-1 line-clamp-2 text-sm leading-5 text-[#5e5e5e]">
                          {workspace.description}
                        </p>
                      )}

                      {updatedAt && (
                        <p className="mt-3 text-xs leading-5 text-[#afafaf]">
                          Updated {updatedAt}
                        </p>
                      )}
                    </button>

                    <div className="mt-4 flex justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPendingDeleteId(workspace.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

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
                    Couldn&apos;t create it. Please try again.
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
                  disabled={!name.trim() || createMutation.isPending}
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
      </div>
    </main>
  );
}
