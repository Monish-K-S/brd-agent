import { Link } from "react-router-dom";
import type { CSSProperties, ReactNode } from "react";
import { useAuth } from "@/auth/useAuth";
import { Wordmark } from "@/components/brand/Wordmark";
import { FieldBackdrop } from "@/components/brand/FieldBackdrop";
import { SignalDot } from "@/components/ui/status";

const OUTLINE_CTA =
  "press inline-flex min-h-11 items-center rounded-full border border-ink/25 bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:border-ink/50 hover:bg-soft";
const PRIMARY_CTA =
  "press inline-flex min-h-11 items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-surface transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep";

export function ErrorHero({
  overline,
  title,
  body,
  children,
}: {
  overline: string;
  title: ReactNode;
  body: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-[1280px] text-center">
      <div aria-hidden="true" className="flex justify-center">
        <SignalDot />
      </div>

      <p className="mt-4 text-xs font-medium text-steel">{overline}</p>

      <h1 className="animate-rise mx-auto mt-4 max-w-2xl font-display text-h1 leading-[1.1] font-normal text-ink sm:text-display sm:leading-[1.08]">
        {title}
      </h1>

      <p
        style={{ animationDelay: "90ms" }}
        className="animate-rise mx-auto mt-4 max-w-xl text-base leading-7 text-steel sm:text-lg sm:leading-8"
      >
        {body}
      </p>

      <div
        style={{ animationDelay: "160ms" }}
        className="animate-rise mt-8 flex flex-wrap items-center justify-center gap-3"
      >
        {children}
      </div>
    </div>
  );
}

/* Editorial "missing source" mark: a document outline whose final rule
   breaks off mid-line. Decorative. */
function MissingSourceMark() {
  return (
    <div aria-hidden="true" className="mx-auto w-44">
      <div className="border border-hairline bg-surface px-5 py-4 shadow-paper">
        <div className="space-y-2">
          <span className="block h-1.5 w-full rounded-full bg-hairline" />
          <span className="block h-1.5 w-5/6 rounded-full bg-hairline" />
          <span className="block h-1.5 w-4/6 rounded-full bg-hairline" />
          <span className="relative block h-1.5 w-2/6 rounded-full bg-hairline">
            <span className="absolute -right-3 top-1/2 size-1.5 -translate-y-1/2 rounded-full bg-signal" />
          </span>
        </div>
      </div>
    </div>
  );
}

export default function NotFoundPage({
  overline = "404",
  title = <>Looks like this source went missing.</>,
  body = "The link you followed may be broken, or the page may have moved.",
}: {
  overline?: string;
  title?: ReactNode;
  body?: ReactNode;
}) {
  const { user, loading } = useAuth();
  const home = !loading && user ? "/workspaces" : "/";
  const homeLabel = !loading && user ? "Back to workspaces" : "Back to home";

  return (
    <main className="relative flex min-h-screen flex-col text-ink">
      <FieldBackdrop intensity="expressive" />

      <header className="sticky top-0 border-b border-hairline bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <Link to="/" aria-label="Sourcify home">
            <Wordmark size="sm" />
          </Link>

          {loading || user ? null : (
            <Link to="/auth" className={OUTLINE_CTA}>
              Sign in
            </Link>
          )}
        </div>
      </header>

      <section className="flex flex-1 items-center px-4 py-16 sm:px-8">
        <div className="mx-auto w-full max-w-[1280px] text-center">
          <p className="animate-rise font-display text-hero leading-[1] text-ink/12">
            {overline}
          </p>

          <div className="reveal mt-8" style={{ "--reveal-delay": "120ms" } as CSSProperties}>
            <MissingSourceMark />
          </div>

          <h1 className="animate-rise mx-auto mt-10 max-w-2xl font-display text-display leading-[1.08] font-normal text-ink [text-wrap:balance]" style={{ animationDelay: "160ms" }}>
            {title}
          </h1>

          <p
            style={{ animationDelay: "230ms" }}
            className="animate-rise mx-auto mt-4 max-w-xl text-base leading-7 text-steel sm:text-lg sm:leading-8"
          >
            {body}
          </p>

          <div
            style={{ animationDelay: "300ms" }}
            className="animate-rise mt-8 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to={home} className={PRIMARY_CTA}>
              {homeLabel}
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <Wordmark size="sm" />
          <p className="text-sm text-steel">
            From scattered files to a structured document.
          </p>
        </div>
      </footer>
    </main>
  );
}
