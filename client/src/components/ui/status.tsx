import { useEffect, useState, type ReactNode } from "react";
import { cn } from "cn";

/* Shared status primitives: quiet sentence-case labels, pills, empty
   states, alerts. Warm neutrals with hairline borders; the coral signal
   dot (SignalDot) is the app's one status signature — small markers,
   never structure. */

export function SignalDot({ className }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn("inline-block size-2 shrink-0 rounded-full bg-signal", className)}
    />
  );
}

export function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p className={cn("text-xs font-medium text-steel", className)}>
      {children}
    </p>
  );
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border border-hairline bg-surface px-6 py-12 text-center sm:px-10 sm:py-14",
        className,
      )}
    >
      <h2 className="font-display text-h3 font-normal text-ink">{title}</h2>

      <p className="mx-auto mt-2 max-w-sm text-base leading-6 text-steel">
        {description}
      </p>

      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function FlashNote({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(false), 3000);

    return () => window.clearTimeout(timer);
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <p
      role="status"
      className={cn(
        "reveal inline-flex items-center rounded-full bg-primary px-4 py-1.5 text-sm font-medium text-surface",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function StateAlert({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "border border-hairline border-l-2 border-l-ink bg-surface px-4 py-3 text-sm leading-6 text-ink",
        className,
      )}
    >
      {children}
    </div>
  );
}
