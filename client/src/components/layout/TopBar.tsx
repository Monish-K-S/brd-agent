import type { ReactNode } from "react";

type TopBarProps = {
  left: ReactNode;
  right?: ReactNode;
};

export function TopBar({ left, right }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-black/8 bg-white px-4 py-4 sm:px-8">
      <div className="mx-auto flex w-full max-w-[1280px] min-w-0 items-center justify-between gap-4">
      <div className="flex min-w-0 items-center gap-4">{left}</div>

      {right && (
        <div className="flex shrink-0 items-center gap-3">{right}</div>
      )}
      </div>
    </header>
  );
}
