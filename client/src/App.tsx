import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/auth/RequireAuth";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import AuthPage from "@/pages/AuthPage";
import LandingPage from "@/pages/LandingPage";
import NotFoundPage from "@/pages/NotFoundPage";
import WorkspacePage from "@/pages/WorkspacePage";
import WorkspacesPage from "@/pages/WorkspacesPage";

// Developer tooling, never shipped to production. `import.meta.env.DEV` is
// substituted with `false` in a production build, which lets the bundler
// drop this branch — and the dynamic import with it. The build is checked
// for any trace of "evals" rather than trusting the flag alone.
const EvalsPage = import.meta.env.DEV
  ? lazy(() => import("@/pages/EvalsPage"))
  : null;

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />

          <Route element={<RequireAuth />}>
            <Route path="/workspaces" element={<WorkspacesPage />} />
            <Route
              path="/workspaces/:id"
              element={
                <ErrorBoundary>
                  <WorkspacePage />
                </ErrorBoundary>
              }
            />
            {EvalsPage && (
              <Route
                path="/evals"
                element={
                  <Suspense fallback={null}>
                    <EvalsPage />
                  </Suspense>
                }
              />
            )}
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
