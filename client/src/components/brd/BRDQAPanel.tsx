import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { askBRD, type BRDQAResponse } from "@/api/brd";
import { Button } from "@/components/ui/button";
import { Bot, Loader2, Send, Trash2 } from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: BRDQAResponse["sources"];
};

type BRDQAPanelProps = {
  workspaceId: string;
};

export function BRDQAPanel({ workspaceId }: BRDQAPanelProps) {
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
    <aside className="flex min-h-0 flex-col border-t border-black/8 bg-white print:hidden md:h-[calc(100vh-81px)] md:border-t-0 md:border-l">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-black/8 px-5 py-4">
        <div className="flex min-w-0 items-center gap-2">
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-full border border-black/8"
          >
            <Bot />
          </span>

          <div className="min-w-0">
            <h2 className="font-mono text-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase">
              Q&A
            </h2>

            <p className="truncate text-xs text-[#999999]">
              Ask about this project
            </p>
          </div>
        </div>

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
      </div>

      {/* Messages */}
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="flex h-full min-h-[260px] flex-col items-center justify-center text-center">
            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-full border border-black/8"
            >
              <Bot />
            </span>

            <h3 className="mt-4 text-base font-medium text-black">
              Ask about your project
            </h3>

            <p className="mt-2 max-w-[240px] text-sm leading-5 text-[#999999]">
              Ask about requirements, objectives, stakeholders, decisions, or
              where information came from.
            </p>
          </div>
        )}

        {messages.length > 0 && (
          <div className="space-y-5">
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
                      ? "max-w-[90%] rounded-[4px] border border-black/8 bg-[#f7f7f7] px-4 py-3 text-sm leading-5 text-black"
                      : "max-w-[95%]"
                  }
                >
                  {message.role === "assistant" && (
                    <div className="mb-2 flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className="flex size-6 items-center justify-center rounded-full border border-black/8"
                      >
                        <Bot />
                      </span>

                      <span className="font-mono text-[10px] font-medium tracking-[0.5px] text-[#999999] uppercase">
                        BRD Agent
                      </span>
                    </div>
                  )}

                  <p className="whitespace-pre-wrap text-sm leading-6 text-black">
                    {message.content}
                  </p>

                  {message.role === "assistant" &&
                    message.sources &&
                    message.sources.length > 0 && (
                      <div className="mt-4 border-t border-black/8 pt-3">
                        <p className="font-mono text-[10px] font-medium tracking-[0.5px] text-[#999999] uppercase">
                          Sources
                        </p>

                        <div className="mt-2 space-y-1.5">
                          {message.sources.map((source) => (
                            <div
                              key={source.id}
                              className="rounded-[4px] border border-black/8 bg-white px-3 py-2"
                            >
                              <p
                                className="truncate text-xs font-medium text-black"
                                title={source.title ?? "Untitled source"}
                              >
                                {source.title ?? "Untitled source"}
                              </p>

                              <p className="mt-1 font-mono text-[10px] font-medium tracking-[0.5px] text-[#999999] uppercase">
                                {source.source_type}
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
              <div className="flex justify-start">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      aria-hidden="true"
                      className="flex size-6 items-center justify-center rounded-full border border-black/8"
                    >
                      <Bot />
                    </span>

                    <span className="font-mono text-[10px] font-medium tracking-[0.5px] text-[#999999] uppercase">
                      BRD Agent
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-[#999999]">
                    <Loader2 className="animate-spin" />
                    Thinking...
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {askMutation.isError && (
          <div className="mt-4 rounded-[4px] border border-black/8 bg-white p-3">
            <p className="text-xs font-medium text-black" role="alert">
              Failed to get an answer. Please try again.
            </p>
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-black/8 bg-white p-4"
      >
        <div className="rounded-[4px] border border-black/12 bg-white p-2 focus-within:border-black">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question..."
            rows={3}
            maxLength={2000}
            disabled={askMutation.isPending}
            className="block w-full resize-none border-0 bg-transparent px-2 py-1 text-sm leading-5 text-black outline-none placeholder:text-[#999999]"
          />

          <div className="mt-2 flex items-center justify-between gap-2 px-2 pb-1">
            <span className="text-[10px] text-[#999999]">
              {question.length}/2000
            </span>

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
