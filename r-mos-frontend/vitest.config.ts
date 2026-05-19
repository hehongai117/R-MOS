import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  define: {
    "import.meta.env.VITE_MODEL_BASE_URL": JSON.stringify("/models"),
  },
  test: {
    include: [
      "src/adjudication/__tests__/adjudication.vitest.test.ts",
      "src/adjudication/**/__tests__/**/*.test.{ts,tsx}",
      "src/api/**/__tests__/**/*.test.{ts,tsx}",
      "src/components/**/__tests__/**/*.test.{ts,tsx}",
      "src/pages/**/__tests__/**/*.test.{ts,tsx}",
      "src/teaching/**/__tests__/**/*.test.{ts,tsx}",
      "src/store/**/__tests__/**/*.test.{ts,tsx}",
      "src/types/**/__tests__/**/*.test.{ts,tsx}",
      "src/config/**/__tests__/**/*.test.{ts,tsx}",
      "src/hooks/**/__tests__/**/*.test.{ts,tsx}",
    ],
    environment: "jsdom",
    globals: true,
    clearMocks: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
