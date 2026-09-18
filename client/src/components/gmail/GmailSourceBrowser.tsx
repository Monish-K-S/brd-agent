import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 print:hidden">
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-white text-black shadow-[0_4px_16px_rgba(0,0,0,0.16)]">
        <div className="flex items-center justify-between gap-4 p-6">
          <h2 className="text-2xl leading-8 font-bold text-black">
            Add emails
          </h2>

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
              className="h-11 min-w-0 flex-1 rounded-lg bg-[#efefef] px-4 text-base text-black outline-none placeholder:text-[#afafaf] focus:bg-[#e2e2e2]"
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
            <div className="space-y-2" aria-label="Loading emails">
              {[0, 1, 2].map((index) => (
                <div key={index} className="rounded-2xl bg-[#efefef] p-4">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="mt-2 h-3 w-1/3" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#efefef] p-4">
              <p className="text-sm text-black">Couldn&apos;t load emails.</p>

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
            </div>
          )}

          {!isLoading && !isError && messages.length === 0 && (
            <p className="py-8 text-center text-sm leading-5 text-[#5e5e5e]">
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
                    className={
                      selected
                        ? "flex cursor-pointer gap-3 rounded-2xl border-2 border-black bg-[#efefef] p-4 transition-colors"
                        : "flex cursor-pointer gap-3 rounded-2xl bg-[#efefef] p-4 transition-colors hover:bg-[#e2e2e2]"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSelection(message.id)}
                      disabled={isImporting}
                      className="mt-1 accent-black"
                    />

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-3">
                        <p className="truncate text-base leading-6 font-medium text-black">
                          {message.subject || "No subject"}
                        </p>

                        <span className="shrink-0 text-xs text-[#afafaf]">
                          {formatDate(message.date)}
                        </span>
                      </div>

                      <p className="mt-1 truncate text-sm leading-5 text-[#5e5e5e]">
                        {message.sender || "Unknown sender"}
                      </p>

                      {message.snippet && (
                        <p className="mt-1 line-clamp-2 text-sm leading-5 text-[#5e5e5e]">
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

        <div className="flex items-center justify-between gap-3 border-t border-black/10 p-4">
          <p className="text-sm text-[#5e5e5e]">
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
      </div>
    </div>
  );
}
