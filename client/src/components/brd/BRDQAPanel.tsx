import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { askBRD, type BRDQAResponse } from "@/api/brd";
import { Button } from "@/components/ui/button";
import { ChevronRight, Loader2, Send, Trash2 } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: BRDQAResponse["sources"];
};

type BRDQAPanelProps = {
  workspaceId: string;
  onCollapse?: () => void;
};

export function BRDQAPanel({ workspaceId, onCollapse }: BRDQAPanelProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const askMutation = useMutation({
    mutationFn: (value: string) => askBRD(workspaceId, value),
  });

  // Latest message (or the spinner) is always in view.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
    });
  }, [messages, askMutation.isPending]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || askMutation.isPending) {
      return;
    }

    // Optimistic: the user's bubble renders instantly, before the round-trip.
    const optimisticId = crypto.randomUUID();

    setMessages((current) => [
      ...current,
      {
        id: optimisticId,
        role: "user",
        content: trimmedQuestion,
      },
    ]);
    setQuestion("");

    askMutation.mutate(trimmedQuestion, {
      onSuccess: (response) => {
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.answer,
            sources: response.sources,
          },
        ]);
      },
      onError: () => {
        // Roll back the optimistic bubble and hand the text back for retry.
        setMessages((current) =>
          current.filter((message) => message.id !== optimisticId),
        );
        setQuestion(trimmedQuestion);
      },
    });
  }

  function handleClear() {
    if (askMutation.isPending) {
      return;
    }

    setMessages([]);
    askMutation.reset();
  }

  return (
    <aside className="order-3 flex min-h-0 flex-col border-t border-hairline bg-surface print:hidden md:order-none md:h-[calc(100vh-var(--shell-chrome))] md:border-t-0 md:border-l">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-hairline px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-medium text-ink">Q&amp;A</h2>
          <p className="truncate text-xs leading-4 text-steel">
            Ask about this project
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {messages.length > 0 && (
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={handleClear}
              disabled={askMutation.isPending}
              aria-label="Clear Q&A"
              title="Clear Q&A"
              className="text-stone hover:text-ink"
            >
              <Trash2 />
            </Button>
          )}

          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              aria-label="Hide Q&A"
              aria-expanded="true"
              title="Hide Q&A"
              className="flex size-9 items-center justify-center rounded-full text-stone transition-colors duration-200 max-md:size-11 hover:bg-soft hover:text-ink"
            >
              <ChevronRight />
            </button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <p className="border-b border-hairline pb-4 text-sm leading-6 text-steel">
            Ask about requirements, decisions, or where something came from.
          </p>
        )}

        {messages.length > 0 && (
          <div className="space-y-5">
            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "animate-in fade-in-0 slide-in-from-bottom-1 duration-200 flex justify-end"
                    : "animate-in fade-in-0 duration-300 flex justify-start"
                }
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[85%] rounded-lg rounded-br-xs bg-soft px-3.5 py-2.5 text-sm leading-5 text-ink"
                      : "w-full"
                  }
                >
                  {message.role === "user" ? (
                    <p className="text-sm leading-5 whitespace-pre-wrap text-ink">
                      {message.content}
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {message.content
                        .split(/\n\s*\n/)
                        .map((paragraph, index) => (
                          <p
                            key={index}
                            lang="en"
                            className="text-justify text-sm leading-6 hyphens-auto whitespace-pre-line text-body"
                          >
                            {paragraph}
                          </p>
                        ))}
                    </div>
                  )}

                  {message.role === "assistant" &&
                    message.sources &&
                    message.sources.length > 0 && (
                      <div className="mt-4 border-t border-hairline pt-3">
                        <p className="mb-1 text-xs font-medium text-steel">
                          Sources
                        </p>
                        <ul className="divide-y divide-hairline">
                          {message.sources.map((source) => (
                            <li
                              key={source.id}
                              className="flex items-baseline justify-between gap-3 py-1.5"
                            >
                              <p
                                className="min-w-0 truncate text-xs font-medium text-ink"
                                title={source.title ?? "Untitled source"}
                              >
                                {source.title ?? "Untitled source"}
                              </p>
                              <span className="shrink-0 text-[11px] text-steel">
                                {source.source_type}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            ))}

            {askMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-steel">
                <span aria-hidden="true" className="flex items-center gap-1">
                  <span className="size-1.5 animate-pulse rounded-full bg-signal" />
                  <span className="size-1.5 animate-pulse rounded-full bg-signal [animation-delay:150ms]" />
                  <span className="size-1.5 animate-pulse rounded-full bg-signal [animation-delay:300ms]" />
                </span>
                Thinking...
              </div>
            )}
          </div>
        )}

        {askMutation.isError && (
          <div className="mt-4 border-y border-hairline py-3">
            <p className="text-xs text-ink" role="alert">
              Couldn&apos;t answer. Try again.
            </p>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-hairline bg-surface px-4 py-3"
      >
        <div className="rounded-lg border border-hairline bg-canvas/70 p-2 transition-colors duration-200 focus-within:border-ink focus-within:bg-surface">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask... (Enter to send)"
            rows={2}
            maxLength={2000}
            disabled={askMutation.isPending}
            className="block w-full resize-none border-0 bg-transparent px-2 py-1 text-sm leading-5 text-ink outline-none placeholder:text-stone"
          />

          <div className="mt-2 flex items-center justify-end gap-2 px-2 pb-1">
            <Button
              type="submit"
              variant="default"
              size="sm"
              disabled={!question.trim() || askMutation.isPending}
            >
              {askMutation.isPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Send />
              )}
              Ask
            </Button>
          </div>
        </div>
      </form>
    </aside>
  );
}
