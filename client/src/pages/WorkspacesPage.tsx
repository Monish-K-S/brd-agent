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
import {
  createWorkspace,
  deleteWorkspace,
  getWorkspaces,
} from "@/api/workspaces";

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
    <main className="min-h-screen p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Workspaces</h1>

        <Button variant="outline" onClick={handleSignOut}>
          Sign out
        </Button>
      </header>

      <section className="mt-8">
        {isLoading && (
          <p className="text-muted-foreground">Loading workspaces...</p>
        )}

        {isError && (
          <p className="text-destructive">Failed to load workspaces.</p>
        )}

        {!isLoading && !isError && workspaces?.length === 0 && (
          <div className="rounded-lg border p-8 text-center">
            <h2 className="text-lg font-medium">No workspaces yet</h2>

            <p className="mt-2 text-sm text-muted-foreground">
              Create your first workspace to get started.
            </p>
          </div>
        )}

        {!isLoading && !isError && workspaces && workspaces.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {workspaces.map((workspace) => (
              <div key={workspace.id} className="rounded-lg border p-5">
                <button
                  type="button"
                  onClick={() => navigate(`/workspaces/${workspace.id}`)}
                  className="w-full text-left transition hover:opacity-80"
                >
                  <h2 className="font-medium">{workspace.name}</h2>

                  {workspace.description && (
                    <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                      {workspace.description}
                    </p>
                  )}
                </button>

                <div className="mt-4 flex justify-end">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteWorkspace(workspace.id)}
                    disabled={deleteMutation.isPending}
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Delete"}
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
                  <p className="text-sm text-destructive" role="alert">
                    Failed to create workspace. Please try again.
                  </p>
                )}

                {deleteMutation.isError && (
                  <p className="text-sm text-destructive" role="alert">
                    Failed to delete workspace. Please try again.
                  </p>
                )}
              </div>

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
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
    </main>
  );
}
