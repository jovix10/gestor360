import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Vite config for Gestor360.
// - Keeps `REACT_APP_*` env-var prefix (backward compatible with legacy code).
// - Exposes `@` alias to `src/`, matching the CRA + shadcn convention.
// - Dev server binds to 0.0.0.0:3000 to work behind reverse-proxies.
export default defineConfig({
  plugins: [react()],
  envPrefix: ["VITE_", "REACT_APP_"],
  // Some legacy files (src/App.js, src/context/AuthContext.js) contain JSX inside `.js`
  // files. Tell esbuild to treat every JS file as JSX so we don't have to rename them.
  esbuild: {
    loader: "jsx",
    include: /\/src\/.*\.jsx?$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: { ".js": "jsx" },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    // Accept requests through any host (Kubernetes ingress, Vercel preview).
    allowedHosts: true,
    hmr: {
      // The dev proxy terminates HTTPS on the ingress. Force secure WS.
      protocol: "wss",
      clientPort: 443,
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
  },
  build: {
    outDir: "build",
    sourcemap: false,
    chunkSizeWarningLimit: 1200,
  },
});
