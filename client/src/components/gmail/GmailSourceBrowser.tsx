import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  getRecentGmailMessages,
  searchGmailMessages,
  type GmailMessageSummary,
} from "@/api/gmail";

type GmailSourceBrowserProps = {
  onClose: () => void;
  onImport: (messageIds: string[]) => void;
  isImporting: boolean;
};

export function GmailSourceBrowser({
  onClose,
  onImport,
  isImporting,
}: GmailSourceBrowserProps) {
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const recentQuery = useQuery({
    queryKey: ["gmail-recent"],
    queryFn: getRecentGmailMessages,
    enabled: activeSearch === "",
    retry: false,
  });

  const searchQuery = useQuery({
    queryKey: ["gmail-search", activeSearch],
    queryFn: () => searchGmailMessages(activeSearch),
    enabled: activeSearch !== "",
    retry: false,
  });

  const messages: GmailMessageSummary[] =
    activeSearch === "" ? (recentQuery.data ?? []) : (searchQuery.data ?? []);

  const isLoading =
    activeSearch === "" ? recentQuery.isLoading : searchQuery.isLoading;

  const isError =
    activeSearch === "" ? recentQuery.isError : searchQuery.isError;

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedSearch = search.trim();

    setSelectedIds([]);
    setActiveSearch(trimmedSearch);
  }

  function handleClearSearch() {
    setSearch("");
    setActiveSearch("");
    setSelectedIds([]);
  }

  function toggleSelection(messageId: string) {
    setSelectedIds((current) => {
      if (current.includes(messageId)) {
        return current.filter((id) => id !== messageId);
      }

      return [...current, messageId];
    });
  }

  function formatDate(date: string | null) {
    if (!date) {
      return "";
    }

    const parsedDate = new Date(date);

    if (Number.isNaN(parsedDate.getTime())) {
      return date;
    }

    return parsedDate.toLocaleDateString();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-lg border bg-background shadow-lg">
        <div className="flex items-center justify-between border-b p-5">
          <div>
            <h2 className="text-lg font-semibold">Add Gmail sources</h2>

            <p className="mt-1 text-sm text-muted-foreground">
              Select emails to add to this workspace.
            </p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={isImporting}
          >
            Close
          </Button>
        </div>

        <div className="border-b p-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search Gmail..."
              className="h-9 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
              disabled={isImporting}
            />

            <Button type="submit" variant="outline" disabled={isImporting}>
              Search
            </Button>

            {activeSearch !== "" && (
              <Button
                type="button"
                variant="ghost"
                onClick={handleClearSearch}
                disabled={isImporting}
              >
                Clear
              </Button>
            )}
          </form>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {activeSearch === "" && (
            <p className="mb-3 text-sm font-medium">Recent emails</p>
          )}

          {activeSearch !== "" && (
            <p className="mb-3 text-sm font-medium">
              Search results for "{activeSearch}"
            </p>
          )}

          {isLoading && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Loading emails...
            </p>
          )}

          {isError && (
            <p className="py-8 text-center text-sm text-destructive">
              Failed to load Gmail messages.
            </p>
          )}

          {!isLoading && !isError && messages.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No emails found.
            </p>
          )}

          {!isLoading && !isError && messages.length > 0 && (
            <div className="space-y-2">
              {messages.map((message) => {
                const selected = selectedIds.includes(message.id);

                return (
                  <label
                    key={message.id}
                    className="flex cursor-pointer gap-3 rounded-md border p-3 hover:bg-muted/50"
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSelection(message.id)}
                      disabled={isImporting}
                      className="mt-1"
                    />

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <p className="truncate text-sm font-medium">
                          {message.subject || "No subject"}
                        </p>

                        <span className="shrink-0 text-xs text-muted-foreground">
                          {formatDate(message.date)}
                        </span>
                      </div>

                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {message.sender || "Unknown sender"}
                      </p>

                      {message.snippet && (
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {message.snippet}
                        </p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t p-4">
          <p className="text-sm text-muted-foreground">
            {selectedIds.length === 0
              ? "No emails selected"
              : `${selectedIds.length} email${
                  selectedIds.length === 1 ? "" : "s"
                } selected`}
          </p>

          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} disabled={isImporting}>
              Cancel
            </Button>

            <Button
              onClick={() => onImport(selectedIds)}
              disabled={selectedIds.length === 0 || isImporting}
            >
              {isImporting
                ? "Adding..."
                : `Add ${
                    selectedIds.length > 0 ? selectedIds.length : ""
                  } selected`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
