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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createWorkspace, deleteWorkspace, getWorkspaces } from "@/api/workspaces";
import { TopBar } from "@/components/layout/TopBar";
import { Skeleton } from "@/components/ui/skeleton";

export default function WorkspacesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const {
    data: workspaces,
    isLoading,
    isError,
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

  function handleDeleteWorkspace(id: string) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this workspace?",
    );

    if (!confirmed) {
      return;
    }

    deleteMutation.mutate(id);
  }

  return (
    <main className="min-h-screen bg-white">
      <TopBar
        left={
          <h1 className="text-[28px] leading-[32.2px] font-medium tracking-[-0.42px] text-black">
            Workspaces
          </h1>
        }
        right={
          <Button variant="secondary" onClick={handleSignOut}>
            Sign out
          </Button>
        }
      />

      <div className="mx-auto w-full max-w-[1280px] px-4 py-12 sm:px-8 sm:py-20">

      <section>
        {isLoading && (
          <div
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
            aria-label="Loading workspaces"
          >
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="rounded-[4px] border border-black/8 bg-white p-6"
              >
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="mt-3 h-4 w-full" />
                <Skeleton className="mt-2 h-4 w-1/2" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm font-medium text-black">
            Failed to load workspaces.
          </p>
        )}

        {!isLoading && !isError && workspaces?.length === 0 && (
          <div className="rounded-[4px] border border-black/8 bg-white p-8 text-center sm:p-12">
            <p
              className="font-mono text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase"
            >
              Getting started
            </p>

            <h2 className="mt-4 text-[22px] leading-[25.3px] font-medium tracking-[-0.22px] text-black">
              No workspaces yet
            </h2>

            <p className="mx-auto mt-2 max-w-sm text-[16px] leading-[20.8px] font-normal tracking-[-0.16px] text-[#999999]">
              Create your first workspace to get started.
            </p>
          </div>
        )}

        {!isLoading && !isError && workspaces && workspaces.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {workspaces.map((workspace) => (
              <div
                key={workspace.id}
                className="rounded-[4px] border border-black/8 bg-white p-6 transition-opacity hover:opacity-80"
              >
                <button
                  type="button"
                  onClick={() => navigate(`/workspaces/${workspace.id}`)}
                  className="w-full text-left"
                >
                  <h2 className="text-[16px] leading-[20.8px] font-medium tracking-[-0.16px] text-black">
                    {workspace.name}
                  </h2>

                  {workspace.description && (
                    <p className="mt-2 line-clamp-2 text-[14px] leading-[19.6px] font-normal text-[#999999]">
                      {workspace.description}
                    </p>
                  )}
                </button>

                <div className="mt-4 flex justify-end">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleDeleteWorkspace(workspace.id)}
                    disabled={
                      deleteMutation.isPending &&
                      deleteMutation.variables === workspace.id
                    }
                  >
                    {deleteMutation.isPending &&
                    deleteMutation.variables === workspace.id
                      ? "Deleting..."
                      : "Delete"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="mt-6">
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button>Create Workspace</Button>} />

          <DialogContent>
            <form onSubmit={handleCreateWorkspace}>
              <DialogHeader>
                <DialogTitle>Create Workspace</DialogTitle>

                <DialogDescription>
                  Create a workspace for your project and add sources to it
                  later.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="workspace-name">Project name</Label>

                  <Input
                    id="workspace-name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="My Project"
                    autoFocus
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="workspace-description">Description</Label>

                  <Input
                    id="workspace-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Optional project description"
                  />
                </div>

                {createMutation.isError && (
                  <p className="text-sm font-medium text-black" role="alert">
                    Failed to create workspace. Please try again.
                  </p>
                )}

                {deleteMutation.isError && (
                  <p className="text-sm font-medium text-black" role="alert">
                    Failed to delete workspace. Please try again.
                  </p>
                )}
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="secondary"
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
      </div>
      </div>
    </main>
  );
}
