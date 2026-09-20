import { existsSync, promises as fs } from "node:fs";
import { join } from "node:path";
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Fill the SITE_URL token with the deployed site URL (VITE_SITE_URL).
 *
 * This keeps canonical / og:image absolute URLs — plus robots.txt and
 * sitemap.xml — free of hard-coded domains in the repo. The value is read
 * from the real environment first (e.g. the Netlify UI) and then from
 * .env files. When absent (local dev) the token resolves to
 * http://localhost:5173 so the dev server stays usable; production builds
 * should always set VITE_SITE_URL in the Netlify UI.
 *
 * index.html is rewritten via transformIndexHtml. robots.txt and
 * sitemap.xml live in public/ (copied verbatim to dist/ before the bundle
 * is written), so they are patched on disk in closeBundle, which runs
 * after every file — including the public-dir copy — has been emitted.
 */
const SITE_URL_TOKEN = "__SITE_URL__";

function siteUrlPlugin(siteUrl: string | undefined): Plugin {
  const fallback = "http://localhost:5173";
  const raw = (siteUrl || "").trim().replace(/\/+$/, "");
  const resolved = raw || fallback;
  if (!raw) {
    console.warn(
      "[site-url] VITE_SITE_URL is not set — using " +
        `${fallback} for the site URL token. Set VITE_SITE_URL in production.`,
    );
  }
  return {
    name: "site-url",
    transformIndexHtml(html) {
      return html.split(SITE_URL_TOKEN).join(resolved);
    },
    async closeBundle() {
      const outDir = join(process.cwd(), "dist");
      for (const name of ["robots.txt", "sitemap.xml"]) {
        const file = join(outDir, name);
        if (!existsSync(file)) continue;
        const content = await fs.readFile(file, "utf8");
        if (!content.includes(SITE_URL_TOKEN)) continue;
        await fs.writeFile(file, content.split(SITE_URL_TOKEN).join(resolved));
      }
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [
      react(),
      siteUrlPlugin(process.env.VITE_SITE_URL || env.VITE_SITE_URL),
    ],
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
