import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Replace the __SITE_URL__ token in index.html with the deployed site URL
 * (VITE_SITE_URL). This keeps canonical / og:image absolute URLs without
 * hard-coding a domain in the repo. When the variable is absent we fall back
 * to an obvious placeholder rather than an empty or relative URL.
 */
function siteUrlPlugin(siteUrl: string | undefined): Plugin {
  const resolved =
    (siteUrl || "").replace(/\/+$/, "") || "https://YOUR_DOMAIN.netlify.app";
  return {
    name: "site-url",
    transformIndexHtml(html) {
      return html.split("__SITE_URL__").join(resolved);
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react(), siteUrlPlugin(env.VITE_SITE_URL)],
    server: {
      port: 5173,
      // Dev proxy: lets `npm run dev` talk to the backend with zero setup.
      // The backend URL itself is configurable via BACKEND_ORIGIN for the dev
      // shell only; production always uses the real URL via VITE_API_URL.
      proxy: {
        "/api": {
          target: process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: false,
    },
  };
});
