/**
 * useSOPViewState.ts - 视图/隔离态状态机 hook（底座）
 *
 * 从 SOPMaintenancePage.tsx 抽离：Gate-1/2 视图状态机的全部 state、
 * 派生集合（visible/clickable/faded/reference/subPart 链接、隔离集合、
 * L2 子零件）、以及视图导航/选择/相机回调。
 *
 * 跨 hook 依赖通过参数注入：emitSOPActionEvent / setSelectedScrewId /
 * setRightPanelTab / isFullscreen / runtimeManifest。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { PartInfo } from '@/components/Viewer3D/manifestPartMetadata';
import {
    getL1CameraPreset,
    getL2CameraPreset,
    getLinkDisplayName,
    getLinkDetailParts,
    linkHasDetailParts,
    type CameraPreset,
} from '@/components/Viewer3D/assemblyTree';
import {
    L0_OVERVIEW_PRESET,
    UI_CAPABILITIES,
    type DetailPart,
} from '@/components/Viewer3D/partsManifest';
import type { DetailPartSelection } from '@/data/maintenanceKnowledge';
import type { RuntimeManifestAdapter } from '@/components/Viewer3D/runtimeManifest';
import { buildAutoCameraPreset, type VisibleBounds } from '@/components/Viewer3D/viewerBounds';
import type { SOPActionEvent } from '@/components/Maintenance/SOPPlayerAdjudicated';
import {
    COLLAPSED_EPSILON,
    EXPLODE_DEFAULT_ON_ENTER,
    ISOLATION_FOCUS_PRESET,
    ISOLATION_TORSO_PRESET,
    ISOLATION_UPPER_LIMB_PRESET,
    ISOLATION_LOWER_LIMB_PRESET,
    ISOLATION_MODEL_SCALE_OVERRIDES,
    resolveScrewSpecIdFromDetailPart,
    type BreadcrumbItem,
    type ViewState,
} from './sopMaintenanceConfig';

interface UseSOPViewStateParams {
    partMetadata: Record<string, PartInfo>;
    emitSOPActionEvent: (event: Omit<SOPActionEvent, 'seq'>) => void;
    setSelectedScrewId: (screwId: string | null) => void;
    setRightPanelTab: (tab: string) => void;
    isFullscreen: boolean;
    runtimeManifest: RuntimeManifestAdapter | null;
}

export function useSOPViewState({
    partMetadata,
    emitSOPActionEvent,
    setSelectedScrewId,
    setRightPanelTab,
    isFullscreen,
    runtimeManifest,
}: UseSOPViewStateParams) {
    const [explodeAmount, setExplodeAmount] = useState(0);
    const [hoveredPart, setHoveredPart] = useState<PartInfo | null>(null);
    const [selectedPart, setSelectedPart] = useState<PartInfo | null>(null);
    const [viewMode, setViewMode] = useState<'normal' | 'explode'>('normal');
    const [hoveredDetailSelection, setHoveredDetailSelection] = useState<DetailPartSelection | null>(null);
    const [focusTarget, setFocusTarget] = useState<string | null>(null);
    const lastAutoCameraSignatureRef = useRef('');

    // ============================================================
    // Gate-1: 视图状态机
    // ============================================================
    const [viewState, setViewState] = useState<ViewState>('OVERVIEW');
    const [selectedOverviewNode, setSelectedOverviewNode] = useState<string | null>(null);
    const [breadcrumbPath, setBreadcrumbPath] = useState<BreadcrumbItem[]>([
        { nodeId: null, displayName: '总览' },
    ]);
    const [cameraPreset, setCameraPreset] = useState<CameraPreset>(L0_OVERVIEW_PRESET);
    const coreModelLinkIds = useMemo(() => Object.keys(partMetadata), [partMetadata]);

    // 隔离集合（根据选中的 overview node 计算）
    const isolationSets = useMemo(() => {
        if (viewState !== 'ISOLATED' || !selectedOverviewNode) return null;
        const targetLinks = [selectedOverviewNode];
        const fadeLinks = coreModelLinkIds.filter((linkId) => linkId !== selectedOverviewNode);
        const referenceLinks = [selectedOverviewNode];
        return { targetLinks, fadeLinks, referenceLinks };
    }, [viewState, selectedOverviewNode, coreModelLinkIds]);

    // Gate-2: L2 状态
    const [isolationLevel, setIsolationLevel] = useState(0); // 0=L0, 1=L1, 2=L2
    const [l2TargetLink, setL2TargetLink] = useState<string | null>(null);
    const [l2SelectedPartIdx, setL2SelectedPartIdx] = useState<number | null>(null);
    const [siblingsMode, setSiblingsMode] = useState<'fade' | 'hide'>('fade');

    const canAdjustExplode = viewState === 'ISOLATED' && viewMode === 'explode';
    const effectiveExplodeAmount = canAdjustExplode ? explodeAmount : 0;
    const showFullCoreOnCollapsed = canAdjustExplode && explodeAmount <= COLLAPSED_EPSILON;

    // L1/L2 态下传给 Atom01Interactive 的 props
    const visibleLinks = useMemo(() => {
        if (showFullCoreOnCollapsed) return coreModelLinkIds;
        if (!isolationSets) return coreModelLinkIds;
        return isolationSets.targetLinks;
    }, [showFullCoreOnCollapsed, coreModelLinkIds, isolationSets]);

    const clickableLinks = useMemo(() => {
        if (showFullCoreOnCollapsed) return coreModelLinkIds;
        if (!isolationSets) return coreModelLinkIds;
        // L2 态下仅 l2TargetLink 可点击（其余 target 兄弟 fade）
        if (isolationLevel >= 2 && l2TargetLink) {
            if (UI_CAPABILITIES.allow_cross_jump) {
                return isolationSets.targetLinks;
            }
            return [l2TargetLink];
        }
        return isolationSets.targetLinks;
    }, [showFullCoreOnCollapsed, coreModelLinkIds, isolationSets, isolationLevel, l2TargetLink]);

    const fadedLinks = useMemo(() => {
        if (showFullCoreOnCollapsed) return [];
        if (!isolationSets) return [];
        return [];
    }, [showFullCoreOnCollapsed, isolationSets]);

    const referenceLinks = useMemo(() => {
        if (showFullCoreOnCollapsed) return coreModelLinkIds;
        if (!isolationSets) return coreModelLinkIds;
        return isolationSets.referenceLinks;
    }, [showFullCoreOnCollapsed, coreModelLinkIds, isolationSets]);

    const subPartEnabledLinks = useMemo(() => {
        if (!isolationSets || viewState !== 'ISOLATED') return [];
        if (isolationLevel >= 2 && l2TargetLink) {
            return [l2TargetLink];
        }
        return isolationSets.targetLinks;
    }, [isolationSets, viewState, isolationLevel, l2TargetLink]);

    const l2DetailParts = useMemo(() => {
        if (!l2TargetLink) return [];
        return getLinkDetailParts(l2TargetLink);
    }, [l2TargetLink]);
    const selectedDetailSelection = useMemo<DetailPartSelection | null>(() => {
        if (!l2TargetLink || l2SelectedPartIdx === null) return null;
        return {
            linkName: l2TargetLink,
            partIndex: l2SelectedPartIdx,
        };
    }, [l2TargetLink, l2SelectedPartIdx]);

    const viewerModelScale = viewState === 'ISOLATED'
        ? (selectedOverviewNode ? (ISOLATION_MODEL_SCALE_OVERRIDES[selectedOverviewNode] ?? 1.15) : 1.15)
        : 2;

    // 全屏态提升信息密度：保持隔离语义，提升展开幅度与可读性。
    useEffect(() => {
        if (isFullscreen && viewState === 'ISOLATED' && viewMode === 'explode') {
            setExplodeAmount((prev) => Math.max(prev, 0.35));
        }
    }, [isFullscreen, viewState, viewMode]);

    const handlePartHover = useCallback((part: PartInfo | null) => {
        if (part) {
            setHoveredDetailSelection(null);
        }
        setHoveredPart(part);
    }, []);

    // Gate-1: 进入 L1 隔离态
    const enterIsolation = useCallback((overviewNodeId: string) => {
        lastAutoCameraSignatureRef.current = '';
        setViewState('ISOLATED');
        setIsolationLevel(1);
        setSelectedOverviewNode(overviewNodeId);
        const displayName = partMetadata[overviewNodeId]?.displayName ?? getLinkDisplayName(overviewNodeId);
        setBreadcrumbPath([
            { nodeId: null, displayName: '总览' },
            { nodeId: overviewNodeId, displayName },
        ]);
        setViewMode('explode');
        setExplodeAmount(EXPLODE_DEFAULT_ON_ENTER);
        const isUpperLimb = /(arm|elbow)/.test(overviewNodeId);
        const isTorso = overviewNodeId === 'torso_link';
        const basePreset = isTorso
            ? ISOLATION_TORSO_PRESET
            : isUpperLimb
                ? ISOLATION_UPPER_LIMB_PRESET
                : ISOLATION_LOWER_LIMB_PRESET;
        setCameraPreset(basePreset);
        setSelectedPart(null);
        setHoveredPart(null);
        setHoveredDetailSelection(null);
        setL2TargetLink(null);
        setL2SelectedPartIdx(null);
    }, [partMetadata]);

    // Gate-2: 进入 L2 子零件层
    const enterL2 = useCallback((linkName: string) => {
        lastAutoCameraSignatureRef.current = '';
        setIsolationLevel(2);
        setL2TargetLink(linkName);
        setL2SelectedPartIdx(null);
        const displayName = getLinkDisplayName(linkName);
        setBreadcrumbPath(prev => [
            ...prev.slice(0, 2),
            { nodeId: linkName, displayName },
        ]);
        // 加大爆炸量以充分展示子零件
        setExplodeAmount(Math.max(explodeAmount, 0.4));
        // 相机缩进
        setCameraPreset(ISOLATION_FOCUS_PRESET);
        setSelectedPart(null);
    }, [explodeAmount]);

    const handlePartSelect = useCallback((part: PartInfo | null) => {
        if (part) {
            emitSOPActionEvent({
                type: 'part_selected',
                partName: part.name,
            });
        }
        // 在总览态点击任意核心 link：进入单节点强隔离
        if (viewState === 'OVERVIEW' && part) {
            enterIsolation(part.name);
            return;
        }
        // 在隔离态点击 link：有子零件则进入/切换到 L2，叶子则执行高亮 toggle。
        if (viewState === 'ISOLATED' && part) {
            if (linkHasDetailParts(part.name)) {
                enterL2(part.name);
                return;
            }
        }
        setSelectedPart((prev) => {
            if (!part) return null;
            return prev?.name === part.name ? null : part;
        });
        setSelectedScrewId(null);
        setHoveredDetailSelection(null);
    }, [viewState, enterIsolation, enterL2, emitSOPActionEvent, setSelectedScrewId]);

    // Gate-2: L2 子零件点击（叶子 toggle）
    const handleSubPartSelect = useCallback((linkName: string, partIndex: number, part: DetailPart) => {
        const screwSpecId = part.category === 'screw' ? resolveScrewSpecIdFromDetailPart(part) : null;
        if (screwSpecId) {
            setSelectedScrewId(screwSpecId);
            emitSOPActionEvent({
                type: 'screw_selected',
                screwId: screwSpecId,
            });
        } else {
            setSelectedScrewId(null);
            emitSOPActionEvent({
                type: 'part_selected',
                partName: part.actionTarget ?? linkName,
            });
        }
        const nextSelected = l2SelectedPartIdx === partIndex ? null : partIndex;
        setL2TargetLink(linkName);
        setL2SelectedPartIdx(nextSelected);
        setIsolationLevel(nextSelected === null ? 2 : 3);
        setBreadcrumbPath((prev) => {
            const linkCrumb = { nodeId: linkName, displayName: getLinkDisplayName(linkName) };
            const hasSameLinkCrumb = prev[2]?.nodeId === linkName;
            const base = hasSameLinkCrumb ? prev.slice(0, 3) : [...prev.slice(0, 2), linkCrumb];
            if (nextSelected === null) {
                return base;
            }
            return [
                ...base,
                { nodeId: `${linkName}::${partIndex}`, displayName: part.displayName },
            ];
        });
        // 螺丝点击直接切到螺丝面板，其他保持零件面板
        setRightPanelTab(screwSpecId ? 'tool' : 'part');
        setHoveredDetailSelection(null);
    }, [l2SelectedPartIdx, emitSOPActionEvent, setSelectedScrewId, setRightPanelTab]);

    // Gate-2: L2 子零件 hover
    const handleSubPartHover = useCallback((linkName: string, partIndex: number | null) => {
        if (partIndex === null) {
            setHoveredDetailSelection(null);
            return;
        }
        setHoveredPart(null);
        setHoveredDetailSelection({
            linkName,
            partIndex,
        });
    }, []);

    // Gate-1/2: 返回 L0 总览
    const resetToOverview = useCallback(() => {
        setViewState('OVERVIEW');
        setIsolationLevel(0);
        setSelectedOverviewNode(null);
        setBreadcrumbPath([{ nodeId: null, displayName: '总览' }]);
        setExplodeAmount(0);
        setViewMode('normal');
        setCameraPreset(L0_OVERVIEW_PRESET);
        setSelectedPart(null);
        setHoveredPart(null);
        setHoveredDetailSelection(null);
        setL2TargetLink(null);
        setL2SelectedPartIdx(null);
        setSiblingsMode('fade');
        lastAutoCameraSignatureRef.current = '';
    }, []);

    // Gate-2: 面包屑点击回退到指定层级
    const navigateBreadcrumb = useCallback((idx: number) => {
        if (idx === 0) {
            resetToOverview();
            return;
        }
        const item = breadcrumbPath[idx];
        if (!item) return;

        if (idx === 1 && selectedOverviewNode) {
            // 回到 L1
            setIsolationLevel(1);
            setL2TargetLink(null);
            setL2SelectedPartIdx(null);
            const preset = getL1CameraPreset(selectedOverviewNode);
            if (preset) setCameraPreset(preset);
            setExplodeAmount(EXPLODE_DEFAULT_ON_ENTER);
            setBreadcrumbPath(prev => prev.slice(0, 2));
            setSelectedPart(null);
            return;
        }

        if (idx >= 2 && item.nodeId) {
            const [linkNodeId, detailIndexRaw] = item.nodeId.split('::');
            const detailIndex = detailIndexRaw ? Number(detailIndexRaw) : null;
            setIsolationLevel(detailIndex !== null && Number.isFinite(detailIndex) ? 3 : 2);
            setL2TargetLink(linkNodeId);
            setL2SelectedPartIdx(detailIndex !== null && Number.isFinite(detailIndex) ? detailIndex : null);
            setBreadcrumbPath(prev => prev.slice(0, idx + 1));
            setCameraPreset(getL2CameraPreset(linkNodeId));
            setSelectedPart(null);
        }
    }, [breadcrumbPath, selectedOverviewNode, resetToOverview]);

    // 双击聚焦
    const handlePartDoubleClick = useCallback((part: PartInfo) => {
        setFocusTarget(part.name);
        setTimeout(() => setFocusTarget(null), 100);
    }, []);

    const handleVisibleBoundsChange = useCallback((bounds: VisibleBounds) => {
        const [cx, cy, cz] = bounds.center;
        if (![cx, cy, cz].every(Number.isFinite)) return;

        let nextPreset: CameraPreset;

        if (runtimeManifest) {
            nextPreset = buildAutoCameraPreset(bounds, {
                mode: 'runtime',
                fullscreen: isFullscreen,
            });
        } else if (viewState !== 'ISOLATED') {
            nextPreset = buildAutoCameraPreset(bounds, {
                mode: 'overview',
                fullscreen: isFullscreen,
            });
        } else {
            const radius = Math.min(Math.max(bounds.radius, 0.08), 1.15);
        const isTorso = selectedOverviewNode === 'torso_link';
        const isUpperLimb = selectedOverviewNode ? /(arm|elbow)/.test(selectedOverviewNode) : false;
            nextPreset = buildAutoCameraPreset(
                {
                    center: [cx, cy, cz],
                    radius,
                },
                {
                    mode: 'isolated',
                    fullscreen: isFullscreen,
                    emphasis: isTorso ? 'torso' : isUpperLimb ? 'upper-limb' : 'default',
                },
            );
            if (isolationLevel >= 2) {
                nextPreset = {
                    ...nextPreset,
                    fov: isTorso ? 52 : 44,
                };
            }
        }

        const signature = `${nextPreset.position.map(v => v.toFixed(3)).join(',')}|${nextPreset.target.map(v => v.toFixed(3)).join(',')}|${nextPreset.fov}`;
        if (signature === lastAutoCameraSignatureRef.current) return;
        lastAutoCameraSignatureRef.current = signature;
        setCameraPreset(nextPreset);
    }, [runtimeManifest, viewState, isolationLevel, isFullscreen, selectedOverviewNode]);

    return {
        // state
        viewState,
        selectedOverviewNode,
        breadcrumbPath,
        cameraPreset,
        isolationLevel,
        l2TargetLink,
        l2SelectedPartIdx,
        siblingsMode,
        setSiblingsMode,
        explodeAmount,
        setExplodeAmount,
        hoveredPart,
        selectedPart,
        setSelectedPart,
        viewMode,
        setViewMode,
        hoveredDetailSelection,
        focusTarget,
        // derived
        isolationSets,
        effectiveExplodeAmount,
        visibleLinks,
        clickableLinks,
        fadedLinks,
        referenceLinks,
        subPartEnabledLinks,
        l2DetailParts,
        selectedDetailSelection,
        viewerModelScale,
        // handlers
        handlePartHover,
        enterIsolation,
        enterL2,
        resetToOverview,
        navigateBreadcrumb,
        handlePartSelect,
        handleSubPartSelect,
        handleSubPartHover,
        handlePartDoubleClick,
        handleVisibleBoundsChange,
    };
}
