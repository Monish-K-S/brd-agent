import path from "path"
import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"

// Kept separate from vite.config.ts on purpose: the build config owns the
// manualChunks split for the production bundle, and tests must not be able
// to change what ships.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.test.{ts,tsx}"],
    env: {
      // `@/lib/supabase` and `@/api/client` throw at import time when these
      // are missing, so any test that reaches the transport layer would die
      // on module load rather than on the assertion it was written for.
      VITE_SUPABASE_URL: "http://localhost:54321",
      VITE_SUPABASE_ANON_KEY: "test-anon-key",
      VITE_API_URL: "http://localhost:8000",
    },
  },
})
