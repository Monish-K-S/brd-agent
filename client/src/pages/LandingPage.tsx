import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/auth/useAuth";
import { Eyebrow } from "@/components/ui/status";
import { ChevronDown } from "lucide-react";
import { Wordmark } from "@/components/brand/Wordmark";
import { FieldBackdrop } from "@/components/brand/FieldBackdrop";

const DETAILED_STEPS = [
  {
    title: "Add your sources",
    body: "Upload the files your project already lives in — PDFs and Word documents — or pull in the Gmail threads where the decisions were made. Google Drive files work too.",
  },
  {
    title: "Generate the document",
    body: "Sourcify reads everything, pulls out what matters, and drafts a structured 11-section requirements document for you to react to.",
  },
  {
    title: "Review and export",
    body: "Edit any section in place, ask questions about what was generated, and export the finished document as a PDF or DOCX.",
  },
];

const SOURCE_TYPES = [
  {
    name: "Files",
    body: "PDF, Word, and plain-text documents — the material your project already exists in.",
  },
  {
    name: "Gmail",
    body: "Pick the threads where the decisions were actually made; they become evidence, not attachments.",
  },
  {
    name: "Google Drive",
    body: "Select Drive documents straight from the app and import the same way as uploads.",
  },
];

const BRD_SECTIONS = [
  "Executive summary",
  "Project overview",
  "Business objectives",
  "Scope",
  "Stakeholders",
  "Business requirements",
  "Functional requirements",
  "Non-functional requirements",
  "Assumptions & constraints",
  "Risks & decisions",
  "Open questions",
];

const STATS = [
  { value: "11", label: "Structured sections in every draft" },
  { value: "3", label: "Source types — files, Gmail, Drive" },
  { value: "2", label: "Export formats — PDF and DOCX" },
  { value: "1", label: "Place to edit, ask, and export" },
];

const PRIMARY_CTA =
  "press inline-flex min-h-11 items-center rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-surface transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep";
const OUTLINE_CTA =
  "press inline-flex min-h-11 items-center rounded-full border border-ink/25 bg-transparent px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:border-ink/50 hover:bg-soft";

/* Purely decorative transformation study: scattered fragments resolve
   into an aligned stack. No names, no statuses, no invented data. */
function ScatteredFragments() {
  const scattered = [
    { w: "w-24", rot: "-rotate-6", pos: "left-[6%] top-[12%]", drift: "drift-a" },
    { w: "w-16", rot: "rotate-3", pos: "left-[26%] top-[4%]", drift: "drift-b" },
    { w: "w-28", rot: "-rotate-2", pos: "left-[44%] top-[16%]", drift: "drift-a" },
    { w: "w-14", rot: "rotate-6", pos: "left-[66%] top-[6%]", drift: "drift-b" },
    { w: "w-20", rot: "-rotate-3", pos: "left-[80%] top-[18%]", drift: "drift-a" },
    { w: "w-12", rot: "rotate-2", pos: "left-[14%] top-[38%]", drift: "drift-b" },
    { w: "w-24", rot: "-rotate-4", pos: "left-[54%] top-[40%]", drift: "drift-a" },
    { w: "w-16", rot: "rotate-5", pos: "left-[76%] top-[42%]", drift: "drift-b" },
  ];

  return (
    <div aria-hidden="true" className="relative w-full">
      <div className="relative mx-auto h-28 max-w-xl">
        {scattered.map((s, i) => (
          <span
            key={i}
            className={`absolute h-1.5 rounded-full bg-ink/15 ${s.w} ${s.rot} ${s.pos} ${s.drift}`}
            style={{ animationDelay: `${(i % 4) * 900}ms` }}
          />
        ))}
        <span className="absolute left-1/2 top-[84%] -translate-x-1/2 -translate-y-1/2 rounded-full bg-signal-soft px-4 py-1.5 font-display text-sm text-signal-text">
          SOURCIFY
        </span>
      </div>

      <div className="mx-auto mt-3 flex max-w-xs flex-col items-center">
        <span className="flex h-8 w-px flex-col items-center justify-end bg-edge">
          <ChevronDown aria-hidden="true" className="size-3 translate-y-1/2 text-edge" />
        </span>
        <div className="w-full space-y-2 rounded-xl border border-hairline bg-surface p-5 shadow-level-1">
          {[0.9, 0.72, 0.82, 0.6, 0.76].map((frac, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="size-1 shrink-0 rounded-full bg-signal" />
              <span
                className="h-1.5 rounded-full bg-hairline"
                style={{ width: `${frac * 100}%` }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const { user, loading } = useAuth();

  // Landing stays viewable for everyone. Auth-entry CTAs ("Sign in",
  // "Create your first document") route signed-in users straight to the
  // app; AuthPage forwards them onward if they land there mid-resolve.
  const entry = !loading && user ? "/workspaces" : "/auth";

  return (
    <main className="relative flex min-h-screen flex-col text-ink">
      <FieldBackdrop intensity="strong" />

      <header className="sticky top-0 z-10 border-b border-hairline bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
          <Wordmark size="md" />

          <Link to={entry} className={OUTLINE_CTA}>
            Sign in
          </Link>
        </div>
      </header>

      {/* Hero — editorial, cream field, serif display */}
      <section className="px-4 pt-20 pb-16 sm:px-8 lg:pt-28 lg:pb-20">
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="mx-auto max-w-3xl text-center">
            <Eyebrow className="animate-rise text-signal-text">
              From scattered sources to one document
            </Eyebrow>

            <h1 className="animate-rise mx-auto mt-5 max-w-2xl font-display text-hero leading-[1.02] font-normal text-ink [text-wrap:balance]" style={{ animationDelay: "60ms" }}>
              Messy project information,
              <span className="italic"> neatly structured.</span>
            </h1>

            <p
              style={{ animationDelay: "150ms" }}
              className="animate-rise mx-auto mt-6 max-w-xl text-lead leading-[1.6] font-normal text-steel"
            >
              Sourcify reads your files, emails, and Drive documents — and
              turns them into a requirements document you can edit, ask
              about, and export.
            </p>

            <div
              style={{ animationDelay: "240ms" }}
              className="animate-rise mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
            >
              <Link to={entry} className={PRIMARY_CTA}>
                Create your first BRD
              </Link>

              <a href="#how-it-works" className={OUTLINE_CTA}>
                See how it works
              </a>
            </div>
          </div>

          {/* Transformation study */}
          <div className="reveal mt-16" style={{ "--reveal-delay": "380ms" } as CSSProperties}>
            <ScatteredFragments />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section
        id="how-it-works"
        aria-label="How Sourcify works"
        className="scroll-mt-24 border-t border-hairline bg-surface/60 px-4 py-16 sm:px-8 lg:py-20"
      >
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="reveal-view">
            <h2 className="max-w-2xl font-display text-h1 leading-[1.1] font-normal text-ink">
              Three steps. One document.
            </h2>
          </div>

          <ol className="mt-10">
            {DETAILED_STEPS.map((step, index) => (
              <li
                key={step.title}
                className="reveal-view grid grid-cols-1 gap-2 border-t border-hairline py-8 sm:grid-cols-[auto_1fr] sm:gap-6 lg:grid-cols-[80px_320px_1fr] lg:gap-8"
                style={{ "--reveal-delay": `${index * 90}ms` } as CSSProperties}
              >
                <span
                  aria-hidden="true"
                  className="font-display text-2xl text-signal-text"
                >
                  {String(index + 1).padStart(2, "0")}
                </span>

                <h3 className="text-xl leading-[1.3] font-semibold text-ink">
                  {step.title}
                </h3>

                <p className="max-w-xl text-base leading-[1.6] text-body sm:text-lg">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Sources */}
      <section aria-label="Sources" className="px-4 py-16 sm:px-8 lg:py-20">
        <div className="mx-auto grid w-full max-w-[1280px] gap-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
          <div className="reveal-view lg:sticky lg:top-24 lg:self-start">
            <Eyebrow>What Sourcify reads</Eyebrow>
            <h2 className="mt-3 max-w-md font-display text-h1 leading-[1.1] font-normal text-ink">
              Everything your project already lives in.
            </h2>
          </div>

          <ul>
            {SOURCE_TYPES.map((source, index) => (
              <li
                key={source.name}
                className="reveal-view border-t border-hairline py-6 first:border-t-0 first:pt-0"
                style={{ "--reveal-delay": `${index * 90}ms` } as CSSProperties}
              >
                <div className="flex items-baseline gap-4">
                  <span
                    aria-hidden="true"
                    className="mt-1 size-1.5 shrink-0 self-center rounded-full bg-signal"
                  />
                  <h3 className="text-lg font-semibold text-ink">{source.name}</h3>
                </div>
                <p className="mt-2 max-w-xl pl-[22px] text-base leading-[1.6] text-steel">
                  {source.body}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Structured knowledge — the real 11-section document */}
      <section
        aria-label="The document"
        className="border-t border-hairline bg-surface/60 px-4 py-16 sm:px-8 lg:py-20"
      >
        <div className="mx-auto grid w-full max-w-[1280px] gap-10 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
          <div className="reveal-view lg:sticky lg:top-24 lg:self-start">
            <Eyebrow>Structured knowledge</Eyebrow>
            <h2 className="mt-3 max-w-md font-display text-h1 leading-[1.1] font-normal text-ink">
              A document you can hand to a stakeholder.
            </h2>
            <p className="mt-4 max-w-md text-base leading-[1.6] text-steel">
              Every draft is built from the same eleven sections — numbered,
              editable in place, and mirrored exactly in your PDF and DOCX
              exports.
            </p>
          </div>

          <div className="reveal-view">
            <dl className="grid grid-cols-1 gap-x-10 sm:grid-cols-2">
              {BRD_SECTIONS.map((name, index) => (
                <div
                  key={name}
                  className="flex items-baseline gap-4 border-b border-hairline py-3.5"
                >
                  <dt
                    aria-hidden="true"
                    className="font-display text-sm text-faint tabular-nums"
                  >
                    {String(index + 1).padStart(2, "0")}
                  </dt>
                  <dd className="text-base font-medium text-ink">{name}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      {/* Q&A */}
      <section aria-label="Questions and answers" className="px-4 py-16 sm:px-8 lg:py-20">
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="reveal-view grid gap-10 lg:grid-cols-[1.2fr_1fr] lg:gap-16 lg:items-center">
            <div>
              <Eyebrow>Ask the document</Eyebrow>
              <h2 className="mt-3 max-w-lg font-display text-h1 leading-[1.1] font-normal text-ink">
                Where did this requirement come from?
              </h2>
              <p className="mt-4 max-w-xl text-base leading-[1.6] text-steel">
                Q&A sits beside the document. Ask what the draft is based on
                and get an answer traced back to the sources it was
                generated from — then edit the answer into the section it
                belongs to.
              </p>
            </div>

            {/* Decorative conversation shape — no invented questions. */}
            <div
              aria-hidden="true"
              className="mx-auto w-full max-w-sm space-y-3 rounded-xl border border-hairline bg-surface p-6 shadow-level-1"
            >
              <div className="ml-auto w-2/3 rounded-lg rounded-br-xs bg-soft px-3 py-2">
                <div className="h-1.5 w-full rounded-full bg-ink/12" />
                <div className="mt-1.5 h-1.5 w-3/5 rounded-full bg-ink/12" />
              </div>
              <div className="w-full rounded-lg rounded-bl-xs border border-hairline bg-canvas px-3 py-2">
                <div className="h-1.5 w-11/12 rounded-full bg-hairline" />
                <div className="mt-1.5 h-1.5 w-full rounded-full bg-hairline" />
                <div className="mt-1.5 h-1.5 w-4/5 rounded-full bg-hairline" />
              </div>
              <div className="flex items-center gap-2 pl-1">
                <span className="size-1.5 rounded-full bg-signal" />
                <span className="text-xs text-faint">Sources</span>
                <span className="ml-auto h-1.5 w-16 rounded-full bg-hairline" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stat strip */}
      <section aria-label="What you get" className="px-4 pb-16 sm:px-8 lg:pb-20">
        <div className="mx-auto w-full max-w-[1280px]">
          <dl className="reveal-view grid grid-cols-2 gap-8 lg:grid-cols-4">
            {STATS.map((stat, index) => (
              <div
                key={stat.label}
                className="flex flex-col border-t border-hairline pt-6"
                style={{ "--reveal-delay": `${index * 70}ms` } as CSSProperties}
              >
                <dd className="font-display text-h2 leading-[1.2] font-normal text-ink">
                  {stat.value}
                </dd>
                <dt className="mt-2 text-sm leading-6 text-steel">{stat.label}</dt>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Finale — full-bleed ink band, one coral rule */}
      <section className="relative">
        <div className="bg-primary px-4 py-16 text-canvas sm:px-8 lg:py-20">
          <div className="mx-auto w-full max-w-[1280px] text-center">
            <span
              aria-hidden="true"
              className="mx-auto mb-8 block h-px w-16 bg-signal"
            />
            <h2 className="mx-auto max-w-2xl font-display text-display leading-[1.08] font-normal [text-wrap:balance]">
              Your first document is one upload away.
            </h2>

            <div className="mt-9">
              <Link
                to={entry}
                className="press inline-flex min-h-11 items-center rounded-full bg-canvas px-6 py-[11px] text-sm font-semibold text-ink transition-colors duration-200 hover:bg-surface"
              >
                Create your first BRD
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-primary px-4 py-16 text-canvas sm:px-8">
        <div className="mx-auto w-full max-w-[1280px]">
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <Wordmark tone="light" size="md" />
              <p className="mt-3 max-w-xs text-sm leading-6 text-canvas/60">
                From scattered files to a structured document.
              </p>
            </div>

            <nav aria-label="Product">
              <p className="text-sm font-medium text-canvas">Product</p>
              <ul className="mt-3 space-y-1">
                <li>
                  <a
                    href="#how-it-works"
                    className="inline-block py-1 text-sm leading-6 text-canvas/60 transition-colors duration-200 hover:text-canvas"
                  >
                    How it works
                  </a>
                </li>
                <li>
                  <Link
                    to={entry}
                    className="inline-block py-1 text-sm leading-6 text-canvas/60 transition-colors duration-200 hover:text-canvas"
                  >
                    Create your first BRD
                  </Link>
                </li>
              </ul>
            </nav>

            <nav aria-label="Account">
              <p className="text-sm font-medium text-canvas">Account</p>
              <ul className="mt-3 space-y-1">
                <li>
                  <Link
                    to={entry}
                    className="inline-block py-1 text-sm leading-6 text-canvas/60 transition-colors duration-200 hover:text-canvas"
                  >
                    Sign in
                  </Link>
                </li>
                <li>
                  <Link
                    to="/workspaces"
                    className="inline-block py-1 text-sm leading-6 text-canvas/60 transition-colors duration-200 hover:text-canvas"
                  >
                    Workspaces
                  </Link>
                </li>
              </ul>
            </nav>
          </div>

          <div className="mt-12 border-t border-canvas/10 pt-6">
            <p className="text-xs leading-5 text-canvas/50">
              Sourcify — turn scattered sources into a structured document.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
