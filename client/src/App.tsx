import { Link, BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/auth/RequireAuth";
import AuthPage from "@/pages/AuthPage";
import { Button } from "@/components/ui/button";
import WorkspacesPage from "@/pages/WorkspacesPage"
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
                  <Button asChild className="w-full">
                    <Link to="/auth">Get Started</Link>
                  </Button>

                  <Button asChild variant="outline" className="w-full">
                    <Link to="/auth">Sign In</Link>
                  </Button>
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
