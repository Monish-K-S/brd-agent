import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    rolldownOptions: {
      output: {
        // Keep slow-moving vendor code in long-cacheable chunks so repeat
        // visits only re-download app code.
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules\/(react|react-dom|react-router-dom)\//.test(id))
            return "vendor-react";
          if (id.includes("node_modules/@tanstack/react-query/"))
            return "vendor-query";
          if (/node_modules\/(axios|@supabase)/.test(id)) return "vendor-data";
          if (
            /node_modules\/(@base-ui|class-variance-authority|lucide-react|tw-animate-css)/.test(
              id,
            )
          )
            return "vendor-ui";
          return "vendor";
        },
      },
    },
  },
})
