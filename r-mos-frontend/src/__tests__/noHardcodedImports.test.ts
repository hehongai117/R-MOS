/**
 * 硬编码残留扫描测试
 *
 * 验证模块化改造 Phase 2 Task 22 成果：
 * - 已删除的硬编码数据文件不存在
 * - 没有源文件引用已删除的模块路径
 * - 没有源文件引用 ALL_SOP_SCRIPTS / HARDWARE_SOP_SCRIPTS 常量
 */

import fs from "fs";
import path from "path";
import { describe, it, expect } from "vitest";

const SRC_DIR = path.resolve(__dirname, "..");

// 已删除的硬编码文件路径（相对于 src/）
const DELETED_FILES = [
  "data/sopScripts.ts",
  "data/hardwareSOPScripts.ts",
  "data/sopKneeBearing.ts",
];

// 已删除的模块引用路径模式（import 语句中出现的路径片段）
const DELETED_MODULE_PATHS = [
  "data/sopScripts",
  "data/hardwareSOPScripts",
  "data/sopKneeBearing",
];

// 已删除的常量名称
const DELETED_CONSTANTS = ["ALL_SOP_SCRIPTS", "HARDWARE_SOP_SCRIPTS"];

/**
 * 递归收集目录下所有 .ts / .tsx 源文件，排除测试文件和 __tests__ 目录
 */
function collectSourceFiles(dir: string): string[] {
  const results: string[] = [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      // 排除 __tests__ 目录
      if (entry.name === "__tests__") continue;
      results.push(...collectSourceFiles(fullPath));
    } else if (entry.isFile()) {
      const name = entry.name;
      // 只收集 .ts / .tsx，排除 .test.ts / .test.tsx
      if (
        (name.endsWith(".ts") || name.endsWith(".tsx")) &&
        !name.includes(".test.")
      ) {
        results.push(fullPath);
      }
    }
  }

  return results;
}

describe("硬编码残留扫描", () => {
  describe("已删除的文件不存在", () => {
    for (const relativePath of DELETED_FILES) {
      it(`src/${relativePath} 应已被删除`, () => {
        const absolutePath = path.join(SRC_DIR, relativePath);
        expect(
          fs.existsSync(absolutePath),
          `文件仍然存在: ${absolutePath}`
        ).toBe(false);
      });
    }
  });

  describe("没有源文件 import 已删除的模块", () => {
    const sourceFiles = collectSourceFiles(SRC_DIR);

    for (const deletedPath of DELETED_MODULE_PATHS) {
      it(`不应有文件 import '${deletedPath}'`, () => {
        const violators: string[] = [];

        for (const file of sourceFiles) {
          const content = fs.readFileSync(file, "utf-8");
          // 匹配 import ... from '...data/sopScripts...' 或 require('...')
          if (content.includes(deletedPath)) {
            violators.push(path.relative(SRC_DIR, file));
          }
        }

        expect(
          violators,
          `以下文件仍引用 '${deletedPath}': ${violators.join(", ")}`
        ).toHaveLength(0);
      });
    }
  });

  describe("没有源文件使用已删除的常量", () => {
    const sourceFiles = collectSourceFiles(SRC_DIR);

    for (const constant of DELETED_CONSTANTS) {
      it(`不应有文件使用常量 ${constant}`, () => {
        const violators: string[] = [];

        for (const file of sourceFiles) {
          const content = fs.readFileSync(file, "utf-8");
          if (content.includes(constant)) {
            violators.push(path.relative(SRC_DIR, file));
          }
        }

        expect(
          violators,
          `以下文件仍使用常量 '${constant}': ${violators.join(", ")}`
        ).toHaveLength(0);
      });
    }
  });
});
