import type { ReactNode } from "react";
import { cn } from "cn";

type TopBarProps = {
  left: ReactNode;
  right?: ReactNode;
  /** Contain content to the marketing measure (1280px). The workspace
      shell runs full-bleed so chrome aligns with its grid instead. */
  contained?: boolean;
};

export function TopBar({ left, right, contained = true }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 flex min-h-[calc(var(--shell-chrome)-1px)] items-center justify-between gap-4 border-b border-hairline bg-surface px-4 py-2.5 text-ink sm:px-6">
      <div
        className={cn(
          "mx-auto flex w-full min-w-0 items-center justify-between gap-4",
          contained && "max-w-[1280px]",
        )}
      >
        <div className="flex min-w-0 items-center gap-3">{left}</div>

        {right && (
          <div className="flex shrink-0 items-center gap-3">{right}</div>
        )}
      </div>
    </header>
  );
}
