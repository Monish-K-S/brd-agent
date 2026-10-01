import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/auth/useAuth";
import { supabase } from "@/lib/supabase";
import { Wordmark } from "@/components/brand/Wordmark";
import { FieldBackdrop } from "@/components/brand/FieldBackdrop";
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
    <main className="relative flex min-h-screen flex-col text-ink">
      <FieldBackdrop intensity="soft" />

      <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-4 sm:px-8">
        <Wordmark size="sm" />

        <Link
          to="/"
          aria-label="Back to home"
          className="press flex min-h-11 min-w-11 items-center justify-center rounded-full text-steel outline-none transition-colors duration-200 hover:bg-soft hover:text-ink focus-visible:ring-2 focus-visible:ring-ink/25"
        >
          <ArrowLeft aria-hidden="true" className="size-5" />
        </Link>
      </div>

      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="reveal w-full max-w-md text-center">
          <h1 className="font-display text-h1 leading-[1.1] font-normal text-ink">
            Welcome
          </h1>

          <p className="mt-2 text-base leading-6 text-steel">
            Sign in to continue to your workspaces.
          </p>

          <div className="mt-10 border border-hairline bg-surface px-6 py-8 shadow-paper sm:px-10">
            {error && (
              <p
                className="mb-6 border border-error/30 bg-error/5 px-3 py-2 text-sm text-error"
                role="alert"
              >
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={handleGoogleAuth}
              disabled={loading}
              className="press inline-flex min-h-11 w-full items-center justify-center gap-3 rounded-full bg-primary px-6 py-[11px] text-sm font-semibold text-surface outline-none transition-colors duration-200 hover:bg-primary-deep active:bg-primary-deep focus-visible:ring-3 focus-visible:ring-ink/25 disabled:bg-hairline disabled:text-faint"
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

            <div className="mt-6 space-y-1.5">
              <p className="text-sm text-steel">
                Google sign-in only — no password to remember.
              </p>
              <p className="text-sm text-steel">
                You&apos;ll land in your workspaces right after.
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
