/**
 * @description 基于 esbuild 的裁决测试运行器（无需额外依赖）
 */

import { buildSync } from 'esbuild';
import { mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import { join, dirname } from 'path';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const entry = join(__dirname, '../src/adjudication/__tests__/run-adjudication-tests.ts');
const tempDir = mkdtempSync(join(tmpdir(), 'rmos-adjudication-tests-'));
const outfile = join(tempDir, 'bundle.mjs');

buildSync({
    entryPoints: [entry],
    outfile,
    bundle: true,
    platform: 'node',
    format: 'esm',
    target: 'es2020',
    sourcemap: 'inline',
    define: {
        'import.meta.env.VITE_MODEL_BASE_URL': '"/models"',
    },
});

const result = spawnSync('node', [outfile], { stdio: 'inherit' });
process.exitCode = result.status ?? 1;
