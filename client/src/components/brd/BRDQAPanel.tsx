import { useState, type FormEvent } from "react";
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

  const askMutation = useMutation({
    mutationFn: (value: string) => askBRD(workspaceId, value),

    onSuccess: (response, submittedQuestion) => {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: submittedQuestion,
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
        },
      ]);

      setQuestion("");
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion || askMutation.isPending) {
      return;
    }

    askMutation.mutate(trimmedQuestion);
  }

  function handleClear() {
    if (askMutation.isPending) {
      return;
    }

    setMessages([]);
    askMutation.reset();
  }

  return (
    <aside className="flex min-h-0 flex-col border-t border-black/10 bg-white print:hidden md:h-[calc(100vh-65px)] md:border-t-0 md:border-l">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-black/10 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#efefef] text-black"
          >
            <Bot />
          </span>

          <h2 className="truncate text-base font-medium text-black">Q&A</h2>
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
              className="flex size-9 items-center justify-center rounded-full text-black transition-colors hover:bg-black/5"
            >
              <ChevronRight />
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full min-h-[200px] flex-col items-center justify-center text-center">
            <p className="max-w-[240px] text-sm leading-5 text-[#5e5e5e]">
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
                      ? "max-w-[90%] rounded-2xl bg-black px-4 py-3 text-sm leading-5 text-white"
                      : "max-w-[95%]"
                  }
                >
                  <p
                    className={
                      message.role === "user"
                        ? "whitespace-pre-wrap text-sm leading-5 text-white"
                        : "whitespace-pre-wrap text-sm leading-5 text-black"
                    }
                  >
                    {message.content}
                  </p>

                  {message.role === "assistant" &&
                    message.sources &&
                    message.sources.length > 0 && (
                      <div className="mt-3 border-t border-black/10 pt-2">
                        <div className="mt-2 space-y-1.5">
                          {message.sources.map((source) => (
                            <div
                              key={source.id}
                              className="rounded-2xl bg-[#efefef] px-3 py-2"
                            >
                              <p
                                className="truncate text-xs font-medium text-black"
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
              <div className="flex items-center gap-2 text-sm text-[#5e5e5e]">
                <Loader2 className="animate-spin" />
                Thinking...
              </div>
            )}
          </div>
        )}

        {askMutation.isError && (
          <div className="mt-4 rounded-2xl bg-[#efefef] p-3">
            <p className="text-xs text-black" role="alert">
              Couldn&apos;t answer. Try again.
            </p>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-black/10 bg-white p-4"
      >
        <div className="rounded-lg bg-[#efefef] p-2 focus-within:bg-[#e2e2e2]">
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
            className="block w-full resize-none border-0 bg-transparent px-2 py-1 text-sm leading-5 text-black outline-none placeholder:text-[#afafaf]"
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
