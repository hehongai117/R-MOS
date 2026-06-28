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
      "src/__tests__/**/*.test.{ts,tsx}",
      "src/adjudication/__tests__/adjudication.vitest.test.ts",
      "src/adjudication/*/__tests__/**/*.test.{ts,tsx}",
      "src/api/**/__tests__/**/*.test.{ts,tsx}",
      "src/components/**/__tests__/**/*.test.{ts,tsx}",
      "src/pages/**/__tests__/**/*.test.{ts,tsx}",
      "src/teaching/**/__tests__/**/*.test.{ts,tsx}",
      "src/store/**/__tests__/**/*.test.{ts,tsx}",
      "src/types/**/__tests__/**/*.test.{ts,tsx}",
      "src/config/**/__tests__/**/*.test.{ts,tsx}",
      "src/hooks/**/__tests__/**/*.test.{ts,tsx}",
      "src/data/**/__tests__/**/*.test.{ts,tsx}",
    ],
    environment: "jsdom",
    globals: true,
    clearMocks: true,
    setupFiles: ["./src/test-setup.ts"],
    // Phase 2 测试安全网：守护 Phase 3 待重构巨型文件的行覆盖率，防止重构期回退。
    // 阈值与 docs/superpowers/plans/2026-06-25-phase2-test-safety-net.md 的 Global Constraints 一致。
    coverage: {
      provider: "v8",
      include: [
        "src/pages/SOPMaintenancePage.tsx",
        "src/components/Viewer3D/Atom01Interactive.tsx",
        "src/components/Viewer3D/atom01/SubPartMesh.tsx",
        "src/components/Viewer3D/atom01/SubPartsGroup.tsx",
        "src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx",
        "src/components/Viewer3D/atom01/atom01Geometry.ts",
        "src/components/Maintenance/SOPPlayerAdjudicated.tsx",
      ],
      thresholds: {
        "src/pages/SOPMaintenancePage.tsx": { lines: 70 },
        "src/components/Viewer3D/Atom01Interactive.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/SubPartMesh.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/SubPartsGroup.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/atom01Geometry.ts": { lines: 80 },
        "src/components/Maintenance/SOPPlayerAdjudicated.tsx": { lines: 70 },
      },
    },
  },
});
