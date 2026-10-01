import { cn } from "cn";

export function SignalMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      className={cn("size-4 shrink-0", className)}
      fill="none"
    >
      <path
        d="M2.5 11.5h4M2.5 8h7M2.5 4.5h10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="13" cy="11.5" r="1.6" fill="currentColor" className="text-signal" />
    </svg>
  );
}

export function Wordmark({
  className,
  tone = "ink",
  size = "md",
}: {
  className?: string;
  tone?: "ink" | "light";
  size?: "sm" | "md" | "lg";
}) {
  const text =
    size === "lg"
      ? "text-2xl"
      : size === "sm"
        ? "text-base"
        : "text-lg";
  const mark = size === "lg" ? "size-5" : size === "sm" ? "size-3.5" : "size-4";

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-2 font-display font-normal",
        text,
        tone === "light" ? "text-canvas" : "text-ink",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          "inline-flex items-center justify-center rounded-md",
          size === "lg" ? "size-7" : "size-6",
          tone === "light" ? "bg-canvas" : "bg-ink",
        )}
      >
        <SignalMark
          className={cn(mark, tone === "light" ? "text-ink" : "text-canvas")}
        />
      </span>
      <span className="leading-none">Sourcify</span>
    </span>
  );
}
