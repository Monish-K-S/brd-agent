import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getRecentGmailMessages,
  searchGmailMessages,
  type GmailMessageSummary,
} from "@/api/gmail";
import { isGoogleReconnectRequiredError } from "@/api/googleReconnect";

type GmailSourceBrowserProps = {
  onClose: () => void;
  onImport: (messageIds: string[]) => void;
  isImporting: boolean;
  onReconnect: () => void;
};

export function GmailSourceBrowser({
  onClose,
  onImport,
  isImporting,
  onReconnect,
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
    // One cache entry per distinct term — evict quickly.
    gcTime: 90_000,
  });

  const messages: GmailMessageSummary[] =
    activeSearch === "" ? (recentQuery.data ?? []) : (searchQuery.data ?? []);

  const isLoading =
    activeSearch === "" ? recentQuery.isLoading : searchQuery.isLoading;

  const isError =
    activeSearch === "" ? recentQuery.isError : searchQuery.isError;

  const activeError =
    activeSearch === "" ? recentQuery.error : searchQuery.error;

  const needsReconnect = isGoogleReconnectRequiredError(
    activeError,
    "gmail",
  );

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
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !isImporting) {
          onClose();
        }
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="flex max-h-[85vh] max-w-2xl flex-col gap-0 overflow-hidden p-0 print:hidden sm:max-w-2xl"
      >
        <div className="flex items-center justify-between gap-4 p-6">
          <DialogTitle>
            Add emails
          </DialogTitle>

          <Button
            variant="subtle"
            size="sm"
            onClick={onClose}
            disabled={isImporting}
          >
            Close
          </Button>
        </div>

        <div className="px-6 pb-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search emails..."
              className="h-10 min-w-0 flex-1 rounded-full border border-hairline bg-surface px-4 text-base text-ink outline-none transition-colors placeholder:text-stone focus-visible:border-ink"
              disabled={isImporting}
            />

            <Button type="submit" variant="subtle" disabled={isImporting}>
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

        <div className="min-h-0 flex-1 overflow-y-auto px-6 pb-4">
          {isLoading && (
            <div className="divide-y divide-hairline border-y border-hairline" aria-label="Loading emails">
              {[0, 1, 2].map((index) => (
                <div key={index} className="flex gap-3 py-4">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="mt-2 h-3 w-1/3" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <div className="flex items-center justify-between gap-3 border-y border-hairline py-3">
              <p className="text-sm text-ink">
                {needsReconnect
                  ? "Gmail connection expired."
                  : "Couldn't load emails."}
              </p>

              {needsReconnect ? (
                <Button variant="ghost" size="sm" onClick={onReconnect}>
                  Reconnect
                </Button>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    if (activeSearch === "") {
                      recentQuery.refetch();
                    } else {
                      searchQuery.refetch();
                    }
                  }}
                >
                  Retry
                </Button>
              )}
            </div>
          )}

          {!isLoading && !isError && messages.length === 0 && (
            <p className="py-8 text-center text-sm leading-5 text-steel">
              No emails found.
            </p>
          )}

          {!isLoading && !isError && messages.length > 0 && (
            <ul className="divide-y divide-hairline border-y border-hairline">
              {messages.map((message) => {
                const selected = selectedIds.includes(message.id);

                return (
                  <li key={message.id}>
                  <label
                    className={
                      selected
                        ? "flex cursor-pointer gap-3 border-l-2 border-signal bg-signal-soft/60 px-4 py-4 transition-colors duration-200"
                        : "flex cursor-pointer gap-3 border-l-2 border-transparent px-4 py-4 transition-colors duration-200 hover:bg-soft/60"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSelection(message.id)}
                      disabled={isImporting}
                      className="mt-1 accent-ink"
                    />

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <p className="truncate text-base leading-6 font-medium text-ink">
                          {message.subject || "No subject"}
                        </p>

                        <span className="shrink-0 text-xs text-steel">
                          {formatDate(message.date)}
                        </span>
                      </div>

                      <p className="mt-1 truncate text-sm leading-5 text-steel">
                        {message.sender || "Unknown sender"}
                      </p>

                      {message.snippet && (
                        <p className="mt-1 line-clamp-2 text-sm leading-5 text-steel">
                          {message.snippet}
                        </p>
                      )}
                     </div>
                   </label>
                   </li>
                 );
               })}
             </ul>
           )}
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-hairline bg-canvas/60 px-6 py-4">
          <p className="text-sm text-steel">
            {selectedIds.length === 0
              ? "None selected"
              : `${selectedIds.length} selected`}
          </p>

          <div className="flex gap-3">
            <Button
              variant="subtle"
              onClick={onClose}
              disabled={isImporting}
            >
              Cancel
            </Button>

            <Button
              onClick={() => onImport(selectedIds)}
              disabled={selectedIds.length === 0 || isImporting}
            >
              {isImporting ? "Adding..." : "Add"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
