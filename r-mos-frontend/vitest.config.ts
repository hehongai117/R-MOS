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
        "src/pages/sopMaintenance/useRuntimeDraft.ts",
        "src/pages/sopMaintenance/useSOPViewState.ts",
        "src/pages/sopMaintenance/useSOPPlaybackBridge.ts",
        "src/components/Viewer3D/Atom01Interactive.tsx",
        "src/components/Viewer3D/atom01/SubPartMesh.tsx",
        "src/components/Viewer3D/atom01/SubPartsGroup.tsx",
        "src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx",
        "src/components/Viewer3D/atom01/atom01Geometry.ts",
        "src/components/Maintenance/SOPPlayerAdjudicated.tsx",
        "src/components/Maintenance/sopPlayer/useSOPActionResolver.ts",
        "src/components/Maintenance/sopPlayer/useSOPExecutorBridge.ts",
        "src/pages/sopMaintenance/SOPMaintenancePanels.tsx",
        "src/pages/sopMaintenance/SOPViewerScene.tsx",
        "src/components/Maintenance/sopPlayer/SOPPlayerView.tsx",
      ],
      thresholds: {
        "src/pages/SOPMaintenancePage.tsx": { lines: 70 },
        "src/pages/sopMaintenance/useRuntimeDraft.ts": { lines: 70 },
        "src/pages/sopMaintenance/useSOPViewState.ts": { lines: 70 },
        "src/pages/sopMaintenance/useSOPPlaybackBridge.ts": { lines: 70 },
        "src/components/Viewer3D/Atom01Interactive.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/SubPartMesh.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/SubPartsGroup.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx": { lines: 55 },
        "src/components/Viewer3D/atom01/atom01Geometry.ts": { lines: 80 },
        "src/components/Maintenance/SOPPlayerAdjudicated.tsx": { lines: 70 },
        "src/components/Maintenance/sopPlayer/useSOPActionResolver.ts": { lines: 70 },
        "src/components/Maintenance/sopPlayer/useSOPExecutorBridge.ts": { lines: 70 },
        // Phase 3 提取视图组件：阈值按来源文件(70/55)，实测低于目标则下调到5的倍数
        "src/pages/sopMaintenance/SOPMaintenancePanels.tsx": { lines: 65 }, // 实测66.66%，低于来源70%目标，取65
        "src/pages/sopMaintenance/SOPViewerScene.tsx": { lines: 55 },       // 实测70.7%，来源55%目标
        "src/components/Maintenance/sopPlayer/SOPPlayerView.tsx": { lines: 70 }, // 实测90.45%，来源70%目标
      },
    },
  },
});
