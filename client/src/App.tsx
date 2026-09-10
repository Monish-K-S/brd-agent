import { Link, BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/auth/RequireAuth";
import AuthPage from "@/pages/AuthPage";

import WorkspacesPage from "@/pages/WorkspacesPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <main className="flex min-h-screen items-center justify-center px-4">
              <div className="w-full max-w-sm space-y-6 text-center">
                <div className="space-y-2">
                  <h1 className="text-3xl font-semibold">BRD Agent</h1>

                  <p className="text-muted-foreground">
                    Turn your project sources into a structured BRD.
                  </p>
                </div>

                <div className="flex flex-col gap-3">
                  <Link
                    to="/auth"
                    className="inline-flex h-9 w-full items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-xs transition-colors hover:bg-primary/90"
                  >
                    Get Started
                  </Link>

                  <Link
                    to="/auth"
                    className="inline-flex h-9 w-full items-center justify-center rounded-md border bg-background px-4 py-2 text-sm font-medium shadow-xs transition-colors hover:bg-accent hover:text-accent-foreground"
                  >
                    Sign In
                  </Link>
                </div>
              </div>
            </main>
          }
        />
        <Route path="/auth" element={<AuthPage />} />

        <Route element={<RequireAuth />}>
          <Route path="/workspaces" element={<WorkspacesPage />} />
          <Route path="/workspaces/:id" element={<div>Workspace</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
