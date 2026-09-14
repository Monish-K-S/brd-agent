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
      <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-[4px] border border-black/8 bg-white">
        <div className="flex items-center justify-between border-b border-black/8 p-8">
          <div>
            <p className="font-mono text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
              Gmail
            </p>

            <h2 className="mt-2 text-[22px] leading-[25.3px] font-medium tracking-[-0.22px] text-black">
              Add Gmail sources
            </h2>

            <p className="mt-2 text-[16px] leading-[20.8px] font-normal tracking-[-0.16px] text-[#999999]">
              Select emails to add to this workspace.
            </p>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={onClose}
            disabled={isImporting}
          >
            Close
          </Button>
        </div>

        <div className="border-b border-black/8 p-4">
          <form onSubmit={handleSearch} className="flex gap-3">
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search Gmail..."
              className="h-11 min-w-0 flex-1 rounded-[4px] border border-black/8 bg-white px-4 text-base tracking-[-0.16px] text-black outline-none placeholder:text-[#999999] focus:border-black"
              disabled={isImporting}
            />

            <Button type="submit" variant="secondary" disabled={isImporting}>
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
            <p className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
              Recent emails
            </p>
          )}

          {activeSearch !== "" && (
            <p className="mb-3 font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
              Search results for "{activeSearch}"
            </p>
          )}

          {isLoading && (
            <div className="space-y-2" aria-label="Loading emails">
              {[0, 1, 2].map((index) => (
                <div
                  key={index}
                  className="rounded-[4px] border border-black/8 bg-white p-4"
                >
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="mt-2 h-3 w-1/3" />
                </div>
              ))}
            </div>
          )}

          {isError && (
            <p className="py-8 text-center text-sm font-medium text-black">
              Failed to load Gmail messages.
            </p>
          )}

          {!isLoading && !isError && messages.length === 0 && (
            <p className="py-8 text-center text-[14px] leading-[19.6px] font-normal text-[#999999]">
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
                    className="flex cursor-pointer gap-3 rounded-[4px] border border-black/8 bg-white p-4 transition-colors hover:border-black"
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
                        <p className="truncate text-[16px] leading-[20.8px] font-medium tracking-[-0.16px] text-black">
                          {message.subject || "No subject"}
                        </p>

                        <span className="shrink-0 font-mono text-[11px] tracking-[0.055px] text-[#999999]">
                          {formatDate(message.date)}
                        </span>
                      </div>

                      <p className="mt-1 truncate text-[14px] leading-[19.6px] font-normal text-[#999999]">
                        {message.sender || "Unknown sender"}
                      </p>

                      {message.snippet && (
                        <p className="mt-1 line-clamp-2 text-[14px] leading-[19.6px] font-normal text-[#999999]">
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

        <div className="flex items-center justify-between border-t border-black/8 p-4">
          <p className="text-[14px] leading-[19.6px] font-normal text-[#999999]">
            {selectedIds.length === 0
              ? "No emails selected"
              : `${selectedIds.length} email${
                  selectedIds.length === 1 ? "" : "s"
                } selected`}
          </p>

          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={isImporting}
            >
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
