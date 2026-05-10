/**
 * ModelPreloader.tsx — 模型预加载器
 *
 * 登录后静默预加载爆炸图所需的所有子零件 GLB，
 * 确保用户点击爆炸图时零件能瞬间显示。
 *
 * 使用 drei 的 useGLTF.preload() 将 GLB 下载并解析到内存缓存。
 */

import { useGLTF } from '@react-three/drei';
import { ALL_EXPLODE_PART_URLS } from './partsManifest';
import { getRobotModelBase } from '../../config/robots';

/** 批量大小：每帧处理多少个 URL 的预加载调用 */
const BATCH_SIZE = 8;

/** 批次间隔 (ms) */
const BATCH_DELAY = 100;

/**
 * 预加载所有爆炸图子零件。
 * 分批调用以避免一次性发起过多网络请求。
 * 返回一个 Promise，在全部完成时 resolve。
 */
export function preloadAllParts(
    onProgress?: (loaded: number, total: number) => void,
): Promise<void> {
    const urls = ALL_EXPLODE_PART_URLS;
    const total = urls.length;

    if (total === 0) return Promise.resolve();

    let loaded = 0;

    return new Promise<void>((resolve) => {
        function loadBatch(startIdx: number) {
            const batch = urls.slice(startIdx, startIdx + BATCH_SIZE);

            batch.forEach((url) => {
                try {
                    useGLTF.preload(url);
                } catch {
                    // 静默忽略单个文件的预加载错误
                }
                loaded++;
                onProgress?.(loaded, total);
            });

            if (startIdx + BATCH_SIZE < total) {
                setTimeout(() => loadBatch(startIdx + BATCH_SIZE), BATCH_DELAY);
            } else {
                resolve();
            }
        }

        loadBatch(0);
    });
}

/**
 * 预加载主模型（24 个 robot link）
 * 这些通常在页面加载时就会用到，但可以提前触发。
 */
export function preloadRobotModel(robotId = 'atom01'): void {
    const ROBOT_BASE = getRobotModelBase(robotId);
    const links = [
        'base_link', 'torso_link',
        'left_arm_pitch_link', 'left_arm_roll_link', 'left_arm_yaw_link',
        'left_elbow_pitch_link', 'left_elbow_yaw_link',
        'right_arm_pitch_link', 'right_arm_roll_link', 'right_arm_yaw_link',
        'right_elbow_pitch_link', 'right_elbow_yaw_link',
        'left_thigh_yaw_link', 'left_thigh_roll_link', 'left_thigh_pitch_link',
        'left_knee_link', 'left_ankle_pitch_link', 'left_ankle_roll_link',
        'right_thigh_yaw_link', 'right_thigh_roll_link', 'right_thigh_pitch_link',
        'right_knee_link', 'right_ankle_pitch_link', 'right_ankle_roll_link',
    ];

    links.forEach((name) => {
        try {
            useGLTF.preload(`${ROBOT_BASE}/${name}.glb`);
        } catch {
            // ignore
        }
    });
}

export default preloadAllParts;
