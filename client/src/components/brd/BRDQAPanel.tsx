import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { askBRD, type BRDQAResponse } from "@/api/brd";
import { Button } from "@/components/ui/button";
import { Bot, ChevronRight, Loader2, Send, Trash2 } from "lucide-react";

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
    <aside className="flex min-h-0 flex-col border-t border-hairline-soft bg-canvas print:hidden md:h-[calc(100vh-65px)] md:border-t-0 md:border-l">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-hairline-soft px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface text-ink"
          >
            <Bot />
          </span>

          <h2 className="truncate text-base font-semibold text-ink">Q&A</h2>
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
              className="flex size-9 items-center justify-center rounded-full text-ink transition-colors duration-200 hover:bg-black/5"
            >
              <ChevronRight />
            </button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full min-h-[200px] flex-col items-center justify-center text-center">
            <p className="max-w-[240px] text-sm leading-5 text-steel">
              Ask about requirements, decisions, or where something came from.
            </p>
          </div>
        )}

        {messages.length > 0 && (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[90%] rounded-2xl bg-primary px-4 py-3 text-sm leading-5 text-white"
                      : "max-w-[95%]"
                  }
                >
                  {message.role === "user" ? (
                    <p className="whitespace-pre-wrap text-sm leading-5 text-white">
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
                            className="text-justify text-sm leading-6 hyphens-auto whitespace-pre-line text-ink"
                          >
                            {paragraph}
                          </p>
                        ))}
                    </div>
                  )}

                  {message.role === "assistant" &&
                    message.sources &&
                    message.sources.length > 0 && (
                      <div className="mt-4 border-t border-hairline-soft pt-3">
                        <div className="space-y-1.5">
                          {message.sources.map((source) => (
                            <div
                              key={source.id}
                              className="rounded-2xl border border-hairline bg-surface px-3 py-2"
                            >
                              <p
                                className="truncate text-xs font-medium text-ink"
                                title={source.title ?? "Untitled source"}
                              >
                                {source.title ?? "Untitled source"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              </div>
            ))}

            {askMutation.isPending && (
              <div className="flex items-center gap-2 text-sm text-steel">
                <Loader2 className="animate-spin" />
                Thinking...
              </div>
            )}
          </div>
        )}

        {askMutation.isError && (
          <div className="mt-4 rounded-2xl border border-hairline bg-canvas p-3">
            <p className="text-xs text-ink" role="alert">
              Couldn&apos;t answer. Try again.
            </p>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-hairline-soft bg-canvas p-4"
      >
        <div className="rounded-lg border border-hairline bg-surface p-2 transition-colors duration-200 focus-within:border-ink">
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
