import { Link } from "react-router-dom";

const STEPS = ["Add sources", "Generate the BRD", "Review and export"];

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col bg-white text-black">
      <header className="bg-white">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-4 py-4 sm:px-8">
          <span className="text-base font-medium text-black">BRD Agent</span>

          <Link
            to="/auth"
            className="inline-flex h-11 items-center rounded-full bg-black px-5 text-base font-medium text-white transition-colors hover:bg-black/80"
          >
            Sign in
          </Link>
        </div>
      </header>

      {/* Hero + how it works */}
      <section className="flex flex-1 items-center">
        <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 items-center gap-8 px-4 py-12 sm:px-8 lg:grid-cols-2">
          <div>
            <h1 className="text-[52px] leading-[64px] font-bold text-black">
              Turn project files into a BRD.
            </h1>

            <p className="mt-2 max-w-md text-lg leading-6 font-medium text-[#5e5e5e]">
              Upload documents and emails. Get a structured requirements
              document you can edit and export.
            </p>

            <div className="mt-6">
              <Link
                to="/auth"
                className="inline-flex h-11 items-center rounded-full bg-black px-5 text-base font-medium text-white transition-colors hover:bg-black/80"
              >
                Create your first BRD
              </Link>
            </div>
          </div>

          <div className="rounded-2xl bg-[#efefef] p-6 text-black sm:p-8">
            <h2 className="text-2xl leading-8 font-bold">How it works</h2>

            <ol className="mt-4 space-y-3">
              {STEPS.map((step, index) => (
                <li key={step} className="flex items-center gap-3">
                  <span
                    aria-hidden="true"
                    className="flex size-8 shrink-0 items-center justify-center rounded-full bg-black text-base font-medium text-white"
                  >
                    {index + 1}
                  </span>

                  <span className="text-base font-medium">{step}</span>
                </li>
              ))}
            </ol>

            <Link
              to="/auth"
              className="mt-6 inline-flex h-11 items-center rounded-full bg-black px-5 text-base font-medium text-white transition-colors hover:bg-black/80"
            >
              Get started
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-black/10 bg-white px-4 py-8 sm:px-8">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between">
          <p className="text-sm font-medium text-black">BRD Agent</p>

          <Link
            to="/auth"
            className="text-sm font-medium text-[#5e5e5e] transition-colors hover:text-black"
          >
            Sign in
          </Link>
        </div>
      </footer>
    </main>
  );
}
