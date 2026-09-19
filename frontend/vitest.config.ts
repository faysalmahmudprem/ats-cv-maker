import { defineConfig } from "vitest/config";

// Unit-test config, kept separate from vite.config.ts so the app build is
// untouched. Tests are colocated with the code they cover (*.test.ts[x]).
// jsdom provides localStorage/document for storage.ts, download.ts and the
// component tests (ImportCV state machine, ScoreCard).
export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["src/test/setup.ts"],
  },
});
