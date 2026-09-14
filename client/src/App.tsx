import { Link, BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/auth/RequireAuth";
import AuthPage from "@/pages/AuthPage";
import WorkspacePage from "@/pages/WorkspacePage";
import WorkspacesPage from "@/pages/WorkspacesPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <main className="flex min-h-screen items-center justify-center bg-white px-4 sm:px-8">
              <div className="w-full max-w-sm space-y-6 text-center">
                <div className="space-y-2">
                  <h1 className="text-[52px] leading-[64px] font-bold text-black">
                    BRD Agent
                  </h1>

                  <p className="text-lg font-medium text-[#5e5e5e]">
                    Turn your project sources into a structured BRD.
                  </p>
                </div>

                <div className="flex flex-col gap-3">
                  <Link
                    to="/auth"
                    className="inline-flex h-11 w-full items-center justify-center rounded-full bg-black px-5 py-2 text-base font-medium text-white transition-colors hover:bg-[#282828]"
                  >
                    Get Started
                  </Link>
                </div>
              </div>
            </main>
          }
        />
        <Route path="/auth" element={<AuthPage />} />

        <Route element={<RequireAuth />}>
          <Route path="/workspaces" element={<WorkspacesPage />} />
          <Route path="/workspaces/:id" element={<WorkspacePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
