import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "@/auth/useAuth";
import { CoralDot } from "@/components/ui/status";

const OUTLINE_CTA =
  "inline-flex min-h-11 items-center rounded-full border border-ink bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:bg-black/5";
const PRIMARY_CTA =
  "inline-flex min-h-11 items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep";

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
        <CoralDot />
      </div>

      <p className="mt-4 text-xs font-semibold tracking-[0.08em] text-steel uppercase">
        {overline}
      </p>

      <h1 className="animate-rise mx-auto mt-4 max-w-2xl text-h2 leading-[1.25] font-semibold tracking-[-0.5px] text-ink sm:text-h1 sm:leading-[1.2] sm:tracking-[-1px]">
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

export default function NotFoundPage({
  overline = "404",
  title = <>This page doesn&apos;t exist.</>,
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
    <main className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="sticky top-0 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <Link to="/" className="flex items-center gap-2 text-base font-semibold text-ink">
            <CoralDot />
            BRD Agent
          </Link>

          {loading || user ? null : (
            <Link to="/auth" className={OUTLINE_CTA}>
              Sign in
            </Link>
          )}
        </div>
      </header>

      <section className="flex flex-1 items-center px-4 py-16 sm:px-8">
        <ErrorHero overline={overline} title={title} body={body}>
          <Link to={home} className={PRIMARY_CTA}>
            {homeLabel}
          </Link>
        </ErrorHero>
      </section>

      <footer className="border-t border-hairline-soft">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-2 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="flex items-center gap-2 text-base font-semibold text-ink">
            <CoralDot />
            BRD Agent
          </span>
          <p className="text-sm text-steel">
            From scattered files to a structured BRD.
          </p>
        </div>
      </footer>
    </main>
  );
}
