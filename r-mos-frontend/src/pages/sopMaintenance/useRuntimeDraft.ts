/**
 * useRuntimeDraft.ts - runtime 草案/manifest 状态 hook
 *
 * 从 SOPMaintenancePage.tsx 抽离的最独立单元：维保 runtime 草案、
 * 由草案派生的 manifest 适配器、目标件 id、资产预览路径。
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    buildRobotProjectAssetUrl,
    buildRuntimeSopScript,
    createRuntimeManifestAdapter,
    resolveRuntimeAssetPaths,
    type RuntimeManifestAdapter,
} from '@/components/Viewer3D/runtimeManifest';
import { readMaintenanceWorkspaceSession } from '@/features/maintenance/runtimeWorkspaceSession';
import type { MaintenanceDraftResponse } from '@/types/maintenance';
import type { WorkspaceVariant } from './sopMaintenanceConfig';

interface UseRuntimeDraftParams {
    workspaceVariant: WorkspaceVariant;
    setLinkedSOPId: (sopId: string | null) => void;
    setRightPanelTab: (tab: string) => void;
}

export function useRuntimeDraft({
    workspaceVariant,
    setLinkedSOPId,
    setRightPanelTab,
}: UseRuntimeDraftParams) {
    const [runtimeDraft, setRuntimeDraft] = useState<MaintenanceDraftResponse | null>(null);
    const [runtimeManifest, setRuntimeManifest] = useState<RuntimeManifestAdapter | null>(null);
    const [runtimeTargetIds, setRuntimeTargetIds] = useState<string[]>([]);
    const [runtimeSelectedAssetPath, setRuntimeSelectedAssetPath] = useState<string | null>(null);

    const runtimeSopScript = useMemo(() => {
        if (workspaceVariant === 'demo' || !runtimeDraft) {
            return null;
        }
        return buildRuntimeSopScript(runtimeDraft);
    }, [runtimeDraft, workspaceVariant]);
    const runtimeResolvedAssetPaths = useMemo(() => {
        if (!runtimeManifest) {
            return [];
        }
        return resolveRuntimeAssetPaths(runtimeManifest, runtimeTargetIds);
    }, [runtimeManifest, runtimeTargetIds]);
    const runtimePreviewAssetPath = runtimeSelectedAssetPath ?? runtimeResolvedAssetPaths[0] ?? runtimeManifest?.parts[0] ?? null;
    const runtimePreviewAssetUrl = runtimePreviewAssetPath && runtimeManifest
        ? buildRobotProjectAssetUrl(runtimeManifest.projectId, runtimePreviewAssetPath)
        : null;

    const applyRuntimeDraft = useCallback((draft: MaintenanceDraftResponse) => {
        const manifest = createRuntimeManifestAdapter(draft);
        setRuntimeDraft(draft);
        setRuntimeManifest(manifest);
        const firstTarget = draft.draft.steps[0]?.model_targets ?? [];
        setRuntimeTargetIds(firstTarget);
        setRuntimeSelectedAssetPath(resolveRuntimeAssetPaths(manifest, firstTarget)[0] ?? manifest.parts[0] ?? null);
        setLinkedSOPId(`runtime-${draft.draft_id}`);
        setRightPanelTab('part');
    }, [setLinkedSOPId, setRightPanelTab]);

    useEffect(() => {
        if (workspaceVariant === 'demo') {
            setRuntimeDraft(null);
            setRuntimeManifest(null);
            setRuntimeTargetIds([]);
            setRuntimeSelectedAssetPath(null);
            return;
        }

        const session = readMaintenanceWorkspaceSession();
        if (!session) {
            return;
        }

        if (session.draft) {
            applyRuntimeDraft(session.draft);
        }
    }, [applyRuntimeDraft, workspaceVariant]);

    return {
        runtimeDraft,
        runtimeManifest,
        runtimeTargetIds,
        setRuntimeTargetIds,
        runtimeSelectedAssetPath,
        setRuntimeSelectedAssetPath,
        applyRuntimeDraft,
        runtimeSopScript,
        runtimePreviewAssetPath,
        runtimePreviewAssetUrl,
    };
}
