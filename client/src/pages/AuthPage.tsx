import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
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
    <main className="flex min-h-screen items-center justify-center bg-white px-4 sm:px-8">
      <div className="w-full max-w-sm rounded-2xl bg-[#efefef] p-6 text-center shadow-level-2">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-black">
            Welcome to BRD Agent
          </h1>

          <p className="text-base text-[#5e5e5e]">
            Sign in or create an account to continue.
          </p>
        </div>

        {error && (
          <p className="mt-4 text-sm font-medium text-black" role="alert">
            {error}
          </p>
        )}

        <Button
          type="button"
          className="mt-6 w-full"
          onClick={handleGoogleAuth}
          disabled={loading}
        >
          {loading ? "Continuing..." : "Continue with Google"}
        </Button>
      </div>
    </main>
  );
}
