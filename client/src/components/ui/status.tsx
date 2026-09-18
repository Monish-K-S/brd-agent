import { useEffect, useState, type ReactNode } from "react";
import { cn } from "cn";

/* Shared status primitives: quiet labels, pills, empty states, alerts.
   Black-and-white only, sentence case, no accent color. */

export function Eyebrow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-xs font-medium tracking-normal text-[#5e5e5e] uppercase",
        className,
      )}
    >
      {children}
    </p>
  );
}

type BadgeTone = "neutral" | "filled";

const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-[#efefef] text-black",
  filled: "bg-black text-white",
};

export function StatusBadge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center rounded-full px-3 py-1 text-sm font-medium",
        badgeTones[tone],
        className,
      )}
    >
      <span className="truncate">{children}</span>
    </span>
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
        "rounded-2xl bg-[#efefef] p-8 text-center sm:p-12",
        className,
      )}
    >
      <h2 className="text-2xl leading-8 font-bold text-black">{title}</h2>

      <p className="mx-auto mt-2 max-w-sm text-base leading-6 text-[#5e5e5e]">
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
        "inline-flex items-center rounded-full bg-black px-4 py-1.5 text-sm font-medium text-white",
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
        "rounded-2xl bg-[#efefef] p-4 text-base leading-6 text-black",
        className,
      )}
    >
      {children}
    </div>
  );
}
