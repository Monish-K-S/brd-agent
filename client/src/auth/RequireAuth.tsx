import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "./useAuth"

export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas">
        <p
          role="status"
          aria-label="Loading"
          className="size-6 animate-spin rounded-full border-2 border-hairline border-t-ink"
        />
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace state={{ from: location }} />
  }

  return <Outlet />
}
