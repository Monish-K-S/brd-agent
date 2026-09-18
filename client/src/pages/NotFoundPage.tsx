import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";

const OUTLINE_CTA =
  "inline-flex min-h-11 items-center rounded-full border border-ink bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:bg-black/5";
const PRIMARY_CTA =
  "inline-flex min-h-11 items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep";

export default function NotFoundPage() {
  const { user, loading } = useAuth();
  const home = !loading && user ? "/workspaces" : "/";
  const homeLabel = !loading && user ? "Back to workspaces" : "Back to home";

  return (
    <main className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="sticky top-0 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <Link to="/" className="text-base font-semibold text-ink">
            BRD Agent
          </Link>

          {loading || user ? null : (
            <Link to="/auth" className={OUTLINE_CTA}>
              Sign in
            </Link>
          )}
        </div>
      </header>

      <section className="flex flex-1 items-center px-4 py-24 sm:px-8">
        <div className="mx-auto w-full max-w-[1280px] text-center">
          <p className="text-sm font-semibold tracking-[0.2em] text-stone uppercase">
            404
          </p>

          <h1 className="animate-rise mx-auto mt-4 max-w-2xl text-[40px] leading-[1.1] font-semibold tracking-[-1px] text-ink sm:text-[56px] sm:tracking-[-1.5px]">
            This page doesn&apos;t exist.
          </h1>

          <p
            style={{ animationDelay: "90ms" }}
            className="animate-rise mx-auto mt-4 max-w-xl text-base leading-7 text-steel sm:text-lg sm:leading-8"
          >
            The link you followed may be broken, or the page may have moved.
          </p>

          <div
            style={{ animationDelay: "160ms" }}
            className="animate-rise mt-8 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to={home} className={PRIMARY_CTA}>
              {homeLabel}
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-hairline-soft">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-2 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span className="text-base font-semibold text-ink">BRD Agent</span>
          <p className="text-sm text-stone">
            From scattered files to a structured BRD.
          </p>
        </div>
      </footer>
    </main>
  );
}
