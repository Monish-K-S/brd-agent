import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { supabase } from "@/lib/supabase";
import { useEffect, useState } from "react";

export default function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from
      ?.pathname ?? "/workspaces";

  useEffect(() => {
    if (user) {
      navigate(from, { replace: true });
    }
  }, [user, navigate, from]);

  async function handleGoogleAuth() {
    setError(null);
    setLoading(true);

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/workspaces`,
        skipBrowserRedirect: true,
      },
    });

    if (error) {
      setLoading(false);
      setError(error.message);
      return;
    }

    if (!data.url) {
      setLoading(false);
      setError("Unable to start Google authentication.");
      return;
    }

    window.location.replace(data.url);
  }

  return (
    <main className="flex min-h-screen flex-col bg-white px-4 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-sm">
        <Link
          to="/"
          className="text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase transition-opacity hover:opacity-60"
          style={{
            fontFamily: "ui-monospace,SFMono-Regular,Menlo,monospace",
          }}
        >
          ← Back
        </Link>
      </div>

      <div className="flex flex-1 items-center justify-center py-8">
      <div className="w-full max-w-sm rounded-[4px] border border-black/8 bg-white p-8 text-center">
        <div>
          <p
            className="text-[11px] leading-[11px] font-medium tracking-[0.55px] text-[#999999] uppercase"
            style={{
              fontFamily: "ui-monospace,SFMono-Regular,Menlo,monospace",
            }}
          >
            Sign in
          </p>

          <h1 className="mt-4 text-[28px] leading-[32.2px] font-medium tracking-[-0.42px] text-black">
            Welcome to BRD Agent
          </h1>

          <p className="mt-2 text-[16px] leading-[20.8px] font-normal tracking-[-0.16px] text-[#999999]">
            Sign in or create an account to continue.
          </p>
        </div>

        {error && (
          <p
            className="mt-6 rounded-[4px] border border-black/8 bg-white p-3 text-sm font-medium text-black"
            role="alert"
          >
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={handleGoogleAuth}
          disabled={loading}
          className="mt-6 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-full bg-black px-6 py-3 text-[16px] leading-4 font-medium tracking-[0.08px] text-white uppercase transition-opacity outline-none hover:opacity-80 focus-visible:ring-2 focus-visible:ring-black/50 disabled:pointer-events-none disabled:opacity-50"
          style={{
            fontFamily: "ui-monospace,SFMono-Regular,Menlo,monospace",
          }}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4">
            <path
              fill="#4285F4"
              d="M23.5 12.3c0-.9-.1-1.5-.3-2.3H12v4.5h6.5c-.1 1.1-.8 2.7-2.4 3.8l-.1.3 3.5 2.7.2.1c2.2-2 3.6-5 3.6-9.1z"
            />
            <path
              fill="#34A853"
              d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.8-2.9c-1 .7-2.4 1.2-4.1 1.2-3.1 0-5.8-2.1-6.8-5l-.3.1-3.7 2.9v.2C3.3 21.5 7.3 24 12 24z"
            />
            <path
              fill="#FBBC05"
              d="M5.2 14.4c-.2-.7-.4-1.5-.4-2.4s.1-1.7.4-2.4l-.1-.3-3.6-2.8-.1.1C.5 8.4 0 10.1 0 12s.5 3.6 1.4 5.2l3.8-2.8z"
            />
            <path
              fill="#EA4335"
              d="M12 4.7c1.8 0 3 .8 3.7 1.4l3.3-3.2C17.9 1.1 15.2 0 12 0 7.3 0 3.3 2.5 1.4 6.8l3.8 2.9c1-2.9 3.7-5 6.8-5z"
            />
          </svg>
          {loading ? "Continuing..." : "Continue with Google"}
        </button>
      </div>
      </div>
    </main>
  );
}
