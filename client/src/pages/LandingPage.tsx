import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { CoralDot, Eyebrow } from "@/components/ui/status";
import { FileText, MessagesSquare, PencilLine, FileDown } from "lucide-react";

const DETAILED_STEPS = [
  {
    title: "Add your sources",
    body: "Upload the files your project already lives in — PDFs, Word documents, spreadsheets — or pull in the Gmail threads where the decisions were made.",
  },
  {
    title: "Generate the BRD",
    body: "BRD Agent reads everything, pulls out what matters, and drafts a structured 11-section requirements document for you to react to.",
  },
  {
    title: "Review and export",
    body: "Edit any section in place, ask questions about what was generated, and export the finished BRD as a PDF.",
  },
];

const SOURCES = [
  { name: "Q3-report.pdf" },
  { name: "Notes.docx" },
  { name: "Launch thread" },
];

const DOC_SECTIONS = [
  "Project overview",
  "Objectives",
  "Scope",
  "Stakeholders",
  "Requirements",
];

const STATS = [
  { value: "11", label: "Structured sections in every draft" },
  { value: "3+", label: "Source types — PDF, Word, Gmail" },
  { value: "2", label: "Export formats — PDF and DOCX" },
  { value: "1", label: "Place to edit, ask, and export" },
];

const TILES = [
  {
    icon: FileText,
    title: "Reads your sources",
    body: "Uploads and Gmail threads become the evidence behind every section.",
  },
  {
    icon: PencilLine,
    title: "Edits in place",
    body: "Change any section directly on the page — no round-trips, no re-uploads.",
  },
  {
    icon: MessagesSquare,
    title: "Answers questions",
    body: "Ask where a requirement came from and get an answer traced to sources.",
  },
  {
    icon: FileDown,
    title: "Exports cleanly",
    body: "Take the finished BRD as a paginated PDF or DOCX, mirroring the page.",
  },
];

const PRIMARY_CTA =
  "inline-flex min-h-11 items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-white transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep";
const OUTLINE_CTA =
  "inline-flex min-h-11 items-center rounded-full border border-ink bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:bg-black/5";

export default function LandingPage() {
  const { user, loading } = useAuth();

  // Landing stays viewable for everyone. Auth-entry CTAs ("Sign in",
  // "Create your first BRD") route signed-in users straight to the app;
  // AuthPage forwards them onward if they land there mid-resolve.
  const entry = !loading && user ? "/workspaces" : "/auth";

  return (
    <main className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="sticky top-0 border-b border-hairline-soft bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <span className="flex items-center gap-2 text-base font-semibold text-ink">
            <CoralDot />
            BRD Agent
          </span>

          <Link to={entry} className={OUTLINE_CTA}>
            Sign in
          </Link>
        </div>
      </header>

      {/* Centered hero */}
      <section className="px-4 pt-24 pb-16 sm:px-8 lg:pt-24 lg:pb-20">
        <div className="mx-auto w-full max-w-[1280px] text-center">
          <Eyebrow
            dot
            className="animate-rise justify-center"
          >
            AI-powered requirements
          </Eyebrow>

          <h1 className="animate-rise mx-auto mt-4 max-w-4xl text-h1 leading-[1.1] font-semibold tracking-[-1px] text-ink sm:text-display sm:tracking-[-1.5px] lg:text-hero lg:tracking-[-2px]">
            Turn project files into a BRD.
          </h1>

          <p
            style={{ animationDelay: "90ms" }}
            className="animate-rise mx-auto mt-6 max-w-xl text-lg leading-[1.5] font-medium text-steel"
          >
            Upload documents and emails. Get a structured requirements document
            you can edit and export.
          </p>

          <div
            style={{ animationDelay: "180ms" }}
            className="animate-rise mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <Link to={entry} className={PRIMARY_CTA}>
              Create your first BRD
            </Link>

            <a href="#how-it-works" className={OUTLINE_CTA}>
              See how it works
            </a>
          </div>
        </div>
      </section>

      {/* Source-to-BRD composition */}
      <section className="bg-surface px-4 py-16 sm:px-8 lg:py-20">
        <div
          aria-hidden="true"
          className="mx-auto w-full max-w-[1280px] select-none"
        >
          <div className="mx-auto flex max-w-2xl flex-col items-center">
            <div className="flex flex-wrap justify-center gap-2">
              {SOURCES.map((source) => (
                <span
                  key={source.name}
                  className="inline-flex items-center gap-2 rounded-lg border border-hairline bg-canvas px-3 py-2 text-sm font-medium text-charcoal"
                >
                  <span className="size-2 rounded-full bg-ink" />
                  {source.name}
                </span>
              ))}
            </div>

            <div className="h-8 w-px bg-brand-coral/40" />

            <div className="w-full max-w-sm overflow-hidden rounded-2xl border border-hairline bg-canvas text-left">
              <div
                aria-hidden="true"
                className="h-1 bg-brand-coral"
              />

              <div className="p-5">
              <div className="flex items-center gap-2">
                <span className="size-2.5 rounded-full bg-brand-coral" />
                <p className="text-base font-semibold text-ink">Product BRD</p>
                <p className="ml-auto text-xs text-steel">Draft</p>
              </div>

              <div className="mt-4 space-y-3">
                {DOC_SECTIONS.map((section) => (
                  <div key={section}>
                    <p className="text-sm font-medium text-charcoal">
                      {section}
                    </p>
                    <div className="mt-1.5 h-1.5 rounded-full bg-surface" />
                  </div>
                ))}
              </div>

              <p className="mt-4 text-xs text-steel">
                + 6 more sections, generated from your sources
              </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stat strip */}
      <section aria-label="What you get" className="px-4 py-16 sm:px-8 lg:py-20">
        <div className="mx-auto w-full max-w-[1280px]">
          <dl className="grid grid-cols-2 gap-8 lg:grid-cols-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="flex flex-col">
                <dd className="text-h2 leading-[1.25] font-semibold tracking-[-0.5px] text-ink">
                  {stat.value}
                </dd>
                <dt className="mt-2 text-sm leading-6 text-steel">
                  {stat.label}
                </dt>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Capability tiles */}
      <section
        aria-label="Capabilities"
        className="bg-surface px-4 py-16 sm:px-8 lg:py-20"
      >
        <div className="mx-auto w-full max-w-[1280px]">
          <h2 className="max-w-2xl text-h2 leading-[1.25] font-semibold tracking-[-0.5px] text-ink sm:text-h1 sm:leading-[1.2] sm:tracking-[-1px]">
            Everything around the document, in one place.
          </h2>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {TILES.map((tile) => (
              <div
                key={tile.title}
                className="rounded-3xl border border-hairline bg-canvas p-6"
              >
                <span
                  aria-hidden="true"
                  className="flex size-12 items-center justify-center rounded-full bg-surface text-ink"
                >
                  <tile.icon className="size-5" />
                </span>

                <h3 className="mt-5 text-xl leading-7 font-semibold text-ink">
                  {tile.title}
                </h3>

                <p className="mt-2 text-sm leading-6 text-steel">{tile.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Detailed How it works */}
      <section
        id="how-it-works"
        aria-label="How it works in detail"
        className="scroll-mt-24 px-4 py-16 sm:px-8 lg:py-20"
      >
        <div className="mx-auto w-full max-w-[1280px]">
          <h2 className="max-w-2xl text-h2 leading-[1.25] font-semibold tracking-[-0.5px] text-ink sm:text-h1 sm:leading-[1.2] sm:tracking-[-1px]">
            From scattered files to a finished BRD.
          </h2>

          <ol className="mt-10">
            {DETAILED_STEPS.map((step, index) => (
              <li
                key={step.title}
                className="grid grid-cols-1 gap-2 border-t border-hairline py-8 sm:grid-cols-[auto_1fr] sm:gap-6 lg:grid-cols-[64px_280px_1fr] lg:gap-8"
              >
                <span
                  aria-hidden="true"
                  className="text-2xl font-semibold text-brand-coral"
                >
                  {String(index + 1).padStart(2, "0")}
                </span>

                <h3 className="text-2xl leading-[1.3] font-semibold text-ink">
                  {step.title}
                </h3>

                <p className="max-w-xl text-base leading-[1.5] text-charcoal sm:text-lg">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Coral finale */}
      <section className="px-4 pb-16 sm:px-8 lg:pb-20">
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="rounded-tile bg-brand-coral px-8 py-16 text-center sm:px-16">
            <h2 className="mx-auto max-w-2xl text-h2 leading-[1.2] font-semibold tracking-[-0.5px] text-white sm:text-h1 sm:tracking-[-1px]">
              Your first BRD is one upload away.
            </h2>

            <div className="mt-8">
              <Link
                to={entry}
                className="inline-flex min-h-11 items-center rounded-full border border-white/40 bg-white px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:bg-white/90"
              >
                Create your first BRD
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-primary px-4 py-16 text-white sm:px-8">
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="flex items-center gap-2 text-base font-semibold text-white">
                <CoralDot />
                BRD Agent
              </p>
              <p className="mt-3 max-w-xs text-sm leading-6 text-muted">
                From scattered files to a structured BRD.
              </p>
            </div>

            <nav aria-label="Product">
              <p className="text-sm font-medium text-white">Product</p>
              <ul className="mt-3 space-y-1">
                <li>
                  <a
                    href="#how-it-works"
                    className="inline-block py-1 text-sm leading-6 text-muted transition-colors duration-200 hover:text-white"
                  >
                    How it works
                  </a>
                </li>
                <li>
                  <Link
                    to={entry}
                    className="inline-block py-1 text-sm leading-6 text-muted transition-colors duration-200 hover:text-white"
                  >
                    Create your first BRD
                  </Link>
                </li>
              </ul>
            </nav>

            <nav aria-label="Account">
              <p className="text-sm font-medium text-white">Account</p>
              <ul className="mt-3 space-y-1">
                <li>
                  <Link
                    to={entry}
                    className="inline-block py-1 text-sm leading-6 text-muted transition-colors duration-200 hover:text-white"
                  >
                    Sign in
                  </Link>
                </li>
                <li>
                  <Link
                    to="/workspaces"
                    className="inline-block py-1 text-sm leading-6 text-muted transition-colors duration-200 hover:text-white"
                  >
                    Workspaces
                  </Link>
                </li>
              </ul>
            </nav>
          </div>

          <div className="mt-12 border-t border-white/10 pt-6">
            <p className="text-xs leading-5 text-muted">
              BRD Agent — turn project files into a BRD.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
