import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/auth/RequireAuth";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import AuthPage from "@/pages/AuthPage";
import LandingPage from "@/pages/LandingPage";
import NotFoundPage from "@/pages/NotFoundPage";
import WorkspacePage from "@/pages/WorkspacePage";
import WorkspacesPage from "@/pages/WorkspacesPage";

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
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
