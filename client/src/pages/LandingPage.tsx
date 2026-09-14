import { Link } from "react-router-dom";

const MONO_FONT = "ui-monospace,SFMono-Regular,Menlo,monospace";

function LandingRibbon() {
  return (
    <svg
      viewBox="0 0 560 440"
      role="img"
      aria-label="BRD Agent brand ribbon"
      className="h-auto w-full"
    >
      <defs>
        <linearGradient
          id="brd-ribbon"
          x1="0"
          y1="0"
          x2="560"
          y2="440"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0" stopColor="#fc4c02" />
          <stop offset="0.5" stopColor="#ef2cc1" />
          <stop offset="1" stopColor="#bdbbff" />
        </linearGradient>
      </defs>

      <g fill="none" stroke="url(#brd-ribbon)" strokeLinecap="round">
        <path
          d="M40 360 C 140 340, 180 220, 300 200 S 480 140, 520 60"
          strokeWidth="26"
          opacity="0.9"
        />
        <path
          d="M40 400 C 160 380, 220 260, 340 240 S 480 190, 520 130"
          strokeWidth="14"
          opacity="0.55"
        />
        <path
          d="M60 320 C 150 300, 190 200, 290 185 S 450 130, 490 70"
          strokeWidth="6"
          opacity="0.35"
        />
        <circle cx="470" cy="330" r="46" strokeWidth="10" opacity="0.7" />
        <circle cx="470" cy="330" r="22" strokeWidth="5" opacity="0.4" />
        <circle cx="110" cy="110" r="12" strokeWidth="0" fill="#bdbbff" opacity="0.8" />
        <circle cx="380" cy="90" r="7" strokeWidth="0" fill="#ef2cc1" opacity="0.8" />
        <circle cx="200" cy="360" r="6" strokeWidth="0" fill="#fc4c02" opacity="0.9" />
      </g>
    </svg>
  );
}

const LANDING_STEPS = ["Upload sources", "Generate BRD", "Download & share"];

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col bg-white text-black">
      {/* Mini nav */}
      <header className="border-b border-black/8 bg-white">
        <div className="mx-auto flex w-full max-w-[1280px] items-center justify-between px-4 py-4 sm:px-8">
          <span className="text-[22px] leading-6 font-medium tracking-[-0.22px] text-black">
            BRD Agent
          </span>

          <Link
            to="/auth"
            className="text-base font-normal tracking-[-0.16px] text-black transition-opacity hover:opacity-60"
          >
            Sign in
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-1 items-center bg-white">
        <div className="mx-auto grid w-full max-w-[1280px] grid-cols-1 items-center gap-10 px-4 py-10 sm:px-8 lg:grid-cols-2 lg:py-0">
          <div>
            <p
              className="text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase"
              style={{ fontFamily: MONO_FONT }}
            >
              From sources to spec
            </p>

            <h1 className="mt-4 text-[40px] leading-[48px] font-medium tracking-[-0.8px] text-black sm:text-[64px] sm:leading-[70.4px] sm:tracking-[-1.92px]">
              Turn project sources into a structured BRD.
            </h1>

            <p className="mt-4 max-w-lg text-[18px] leading-[23.4px] font-normal tracking-[-0.18px] text-[#999999]">
              Create a workspace, add documents and Gmail threads, and
              generate a requirements document you can read, edit, and
              export.
            </p>

            <div className="mt-8">
              <Link
                to="/auth"
                className="inline-flex min-h-[44px] items-center justify-center rounded-[4px] bg-black px-6 py-3 text-[16px] leading-4 font-medium tracking-[0.08px] text-white uppercase transition-opacity hover:opacity-80"
                style={{ fontFamily: MONO_FONT }}
              >
                Get started
              </Link>
            </div>

            <ol className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2">
              {LANDING_STEPS.map((step, index) => (
                <li
                  key={step}
                  className="inline-flex items-center gap-2 text-[11px] leading-[11px] font-medium tracking-[0.55px] text-black uppercase"
                  style={{ fontFamily: MONO_FONT }}
                >
                  <span className="text-[#999999]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          <div className="mx-auto w-full max-w-[320px] sm:max-w-[420px] lg:max-w-[520px]">
            <LandingRibbon />
          </div>
        </div>
      </section>
    </main>
  );
}
