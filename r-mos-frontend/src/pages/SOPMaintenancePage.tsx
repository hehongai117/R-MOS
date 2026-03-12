/**
 * SOPMaintenancePage.tsx - SOP 维保系统页面
 * 
 * 功能：
 * - 爆炸图展示机器人零件
 * - 鼠标悬停高亮零件
 * - 点击选中显示零件信息
 * - 爆炸程度滑块控制
 * - 工具选择与校验
 * - 螺丝信息展示
 * - Gate-1: L1 隔离爆炸（选中大部件 → 隔离展开）
 */

import { useState, useCallback, Suspense, useEffect, useMemo, useRef } from 'react';
import { Alert, Button, Card, Col, Descriptions, Empty, Row, Segmented, Select, Space, Tag, Typography, message } from 'antd';
import {
    InfoCircleOutlined,
    EyeOutlined,
    ExpandOutlined,
    FullscreenOutlined,
    FullscreenExitOutlined,
    HomeOutlined,
    RightOutlined,
} from '@ant-design/icons';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useNavigate } from 'react-router-dom';
import { type DiagnosisActionType, runDiagnosisAction } from '@/api/agent-v2';
import { DiagnosisPanel, readLatestDiagnosisResult } from '@/components/DiagnosisPanel/DiagnosisPanel';
import { Atom01Interactive, PartInfo, PART_METADATA } from '@/components/Viewer3D/Atom01Interactive';
import { CameraController } from '@/components/Viewer3D/CameraController';
import DisassemblyDemoAdjudicated from '@/components/Viewer3D/DisassemblyDemoAdjudicated';
import { DisassemblyAnimation } from '@/components/Viewer3D/DisassemblyAnimation';
import PartInspector from '@/components/Viewer3D/PartInspector';
import {
    L0_OVERVIEW_PRESET,
    UI_CAPABILITIES,
    type DetailPart,
} from '@/components/Viewer3D/partsManifest';
import { DetailParts } from '@/components/Viewer3D/DetailParts';
import { preloadAllParts } from '@/components/Viewer3D/ModelPreloader';
import {
    getL1CameraPreset,
    getL2CameraPreset,
    getLinkDisplayName,
    getLinkDetailParts,
    linkHasDetailParts,
    type CameraPreset,
} from '@/components/Viewer3D/assemblyTree';
import {
    SOPMaintenanceExamOverlay,
    SOPMaintenanceHeader,
    SOPMaintenanceLeftRail,
    SOPMaintenanceRightRail,
    ToolSelector,
    ScrewInfo,
} from '@/components/Maintenance';
import { SOPPlayerAdjudicated, type SOPActionEvent } from '@/components/Maintenance/SOPPlayerAdjudicated';
import { ALL_SOP_SCRIPTS } from '@/data/sopScripts';
import {
    getCorePartDetailRecord,
    getDetailPartDetailRecord,
    type DetailPartSelection,
} from '@/data/maintenanceKnowledge';
import { RuntimeAssetPreview } from '@/components/Viewer3D/RuntimeAssetPreview';
import { buildRobotProjectAssetUrl, buildRuntimeSopScript, createRuntimeManifestAdapter, resolveRuntimeAssetPaths, type RuntimeManifestAdapter } from '@/components/Viewer3D/runtimeManifest';
import { readMaintenanceWorkspaceSession, type MaintenanceWorkspaceSession } from '@/features/maintenance/runtimeWorkspaceSession';
import type { MaintenanceDraftResponse } from '@/types/maintenance';
import {
    AdjudicationReport,
    SOPExecutor,
    SOPExecutionContext,
    SOPExecutionState,
    SOPScriptAdjudication,
    SOPStepAdjudication,
    useAdjudicationStore,
} from '@/adjudication';
import { useSOPSceneSync } from '@/adjudication/ui/useSOPSceneSync';
import { scoringEngine } from '@/adjudication/core/scoringEngine';

const { Title, Text } = Typography;
const EXAM_DURATION_MS = 60 * 60 * 1000;
const EXPLODE_DEFAULT_ON_ENTER = 0.4;
const COLLAPSED_EPSILON = 0.0001;
const ISOLATION_FOCUS_PRESET: CameraPreset = {
    position: [0.9, 0, 0.4],
    target: [0, 0, 0],
    fov: 45,
};
const ISOLATION_TORSO_PRESET: CameraPreset = {
    position: [2.2, 0.6, 1.8],
    target: [0, 0.3, 0.4],
    fov: 48,
};
const ISOLATION_UPPER_LIMB_PRESET: CameraPreset = {
    position: [1.45, 0, 0.9],
    target: [0, 0, 0.2],
    fov: 46,
};
const ISOLATION_LOWER_LIMB_PRESET: CameraPreset = {
    position: [1.15, 0, 0.65],
    target: [0, 0, 0.05],
    fov: 45,
};
const ISOLATION_MODEL_SCALE_OVERRIDES: Partial<Record<string, number>> = {
    base_link: 1.1,
    torso_link: 1.05,
    left_arm_pitch_link: 1.25,
    left_arm_roll_link: 1.25,
    left_arm_yaw_link: 1.25,
    left_elbow_pitch_link: 1.25,
    left_elbow_yaw_link: 1.25,
    right_arm_pitch_link: 1.25,
    right_arm_roll_link: 1.25,
    right_arm_yaw_link: 1.25,
    right_elbow_pitch_link: 1.25,
    right_elbow_yaw_link: 1.25,
    left_thigh_yaw_link: 1.2,
    left_thigh_roll_link: 1.2,
    left_thigh_pitch_link: 1.2,
    left_knee_link: 1.2,
    left_ankle_pitch_link: 1.2,
    left_ankle_roll_link: 1.2,
    right_thigh_yaw_link: 1.2,
    right_thigh_roll_link: 1.2,
    right_thigh_pitch_link: 1.2,
    right_knee_link: 1.2,
    right_ankle_pitch_link: 1.2,
    right_ankle_roll_link: 1.2,
};

// ============================================================
// Gate-1: 视图状态类型
// ============================================================
type ViewState = 'OVERVIEW' | 'ISOLATED';

interface BreadcrumbItem {
    nodeId: string | null; // null = 总览
    displayName: string;
}

// 分组中文名
const GROUP_NAMES: Record<string, string> = {
    'base': '底座',
    'torso': '躯干',
    'left_arm': '左臂',
    'right_arm': '右臂',
    'left_leg': '左腿',
    'right_leg': '右腿',
};

const SOP_EXECUTION_STATE_TAG_COLOR: Partial<Record<SOPExecutionState, string>> = {
    [SOPExecutionState.IDLE]: 'blue',
    [SOPExecutionState.PRECONDITION_CHECK]: 'gold',
    [SOPExecutionState.EXECUTING]: 'green',
    [SOPExecutionState.VALIDATION]: 'purple',
    [SOPExecutionState.COMPLETE]: 'cyan',
    [SOPExecutionState.FAILED]: 'red',
    [SOPExecutionState.BLOCKED]: 'red',
};

const SOP_EXECUTION_STATE_LABEL: Partial<Record<SOPExecutionState, string>> = {
    [SOPExecutionState.IDLE]: '就绪',
    [SOPExecutionState.PRECONDITION_CHECK]: '前置检查',
    [SOPExecutionState.EXECUTING]: '执行中',
    [SOPExecutionState.VALIDATION]: '验证中',
    [SOPExecutionState.COMPLETE]: '已完成',
    [SOPExecutionState.FAILED]: '失败',
    [SOPExecutionState.BLOCKED]: '已阻断',
};

const UPPER_BODY_CORE_LINKS = [
    'torso_link',
    'left_arm_pitch_link',
    'left_arm_roll_link',
    'left_arm_yaw_link',
    'left_elbow_pitch_link',
    'left_elbow_yaw_link',
    'right_arm_pitch_link',
    'right_arm_roll_link',
    'right_arm_yaw_link',
    'right_elbow_pitch_link',
    'right_elbow_yaw_link',
] as const;

const REMAINING_CORE_LINKS = [
    'base_link',
    'left_thigh_yaw_link',
    'left_thigh_roll_link',
    'left_thigh_pitch_link',
    'left_knee_link',
    'left_ankle_pitch_link',
    'left_ankle_roll_link',
    'right_thigh_yaw_link',
    'right_thigh_roll_link',
    'right_thigh_pitch_link',
    'right_knee_link',
    'right_ankle_pitch_link',
    'right_ankle_roll_link',
] as const;

type WorkspaceVariant = 'runtime' | 'atom01';
type MaintenanceLayoutMode = 'execution' | 'inspector' | 'full';

interface WorkspaceChrome {
    title: string;
    subtitle: string;
    breadcrumb: string[];
    showDraftEntry: boolean;
}

const WORKSPACE_CHROME: Record<WorkspaceVariant, WorkspaceChrome> = {
    runtime: {
        title: 'SOP 维保系统',
        subtitle: '步骤导航、3D 操作区和工具要求统一在同一工作台内处理',
        breadcrumb: ['维保端', 'SOP 工作台'],
        showDraftEntry: true,
    },
    atom01: {
        title: 'ATOM01 维保工作台',
        subtitle: '保留原有 ATOM01 专用维保体验，直接进入隔离爆炸、裁决和 3D 交互执行。',
        breadcrumb: ['工作台', 'ATOM01 维保工作台'],
        showDraftEntry: false,
    },
};

interface SOPMaintenancePageProps {
    workspaceVariant?: WorkspaceVariant;
    layoutMode?: MaintenanceLayoutMode;
}

function resolveScrewSpecIdFromDetailPart(part: DetailPart): string | null {
    const source = `${part.displayName} ${part.path}`;
    const matched = source.match(/M\s*(\d+)\s*[x×]\s*(\d+)/i);
    if (!matched) return null;
    return `M${matched[1]}x${matched[2]}`;
}

// 加载指示器
const LoadingFallback = () => (
    <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
);

function SOPMaintenancePage({ workspaceVariant = 'runtime', layoutMode }: SOPMaintenancePageProps) {
    const navigate = useNavigate();
    const workspaceChrome = WORKSPACE_CHROME[workspaceVariant];
    const effectiveLayoutMode: MaintenanceLayoutMode = workspaceVariant === 'atom01' ? 'full' : (layoutMode ?? 'execution');
    const showExecutionRail = effectiveLayoutMode !== 'inspector';
    const showInspectorRail = effectiveLayoutMode !== 'execution';
    const [explodeAmount, setExplodeAmount] = useState(0);
    const [hoveredPart, setHoveredPart] = useState<PartInfo | null>(null);
    const [selectedPart, setSelectedPart] = useState<PartInfo | null>(null);
    const [viewMode, setViewMode] = useState<'normal' | 'explode'>('normal');
    const [hoveredDetailSelection, setHoveredDetailSelection] = useState<DetailPartSelection | null>(null);
    const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
    const [linkedSOPId, setLinkedSOPId] = useState<string | null>(null);
    const [isSopListExpanded, setIsSopListExpanded] = useState(false);
    const [sopActionEvent, setSopActionEvent] = useState<SOPActionEvent | null>(null);
    const [selectedScrewId, setSelectedScrewId] = useState<string | null>(null);
    const [rightPanelTab, setRightPanelTab] = useState<string>('part');
    const [focusTarget, setFocusTarget] = useState<string | null>(null);
    const [disassemblyPlaying, setDisassemblyPlaying] = useState(false);
    const [, setDisassemblyStep] = useState<string>('');
    const showDetailParts = false;
    const [runtimeWorkspaceSession, setRuntimeWorkspaceSession] = useState<MaintenanceWorkspaceSession | null>(null);
    const [runtimeDraft, setRuntimeDraft] = useState<MaintenanceDraftResponse | null>(null);
    const [runtimeManifest, setRuntimeManifest] = useState<RuntimeManifestAdapter | null>(null);
    const [runtimeTargetIds, setRuntimeTargetIds] = useState<string[]>([]);
    const [runtimeSelectedAssetPath, setRuntimeSelectedAssetPath] = useState<string | null>(null);
    const [examRemainingMs, setExamRemainingMs] = useState(EXAM_DURATION_MS);
    const [scoreState, setScoreState] = useState(scoringEngine.getState());
    const [diagnosisActionLoading, setDiagnosisActionLoading] = useState(false);
    const [examSummaryReport, setExamSummaryReport] = useState<AdjudicationReport | null>(null);
    const [sopExecutor, setSopExecutor] = useState<SOPExecutor | null>(null);
    const examEndAtRef = useRef<number | null>(null);
    const viewerContainerRef = useRef<HTMLDivElement>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const sopActionSeqRef = useRef(0);
    const lastAutoCameraSignatureRef = useRef('');
    const operationMode = useAdjudicationStore((state) => state.operationMode);
    const setCurrentTool = useAdjudicationStore((state) => state.setCurrentTool);
    const sopSceneSync = useSOPSceneSync();

    // ============================================================
    // Gate-1: 视图状态机
    // ============================================================
    const [viewState, setViewState] = useState<ViewState>('OVERVIEW');
    const [selectedOverviewNode, setSelectedOverviewNode] = useState<string | null>(null);
    const [breadcrumbPath, setBreadcrumbPath] = useState<BreadcrumbItem[]>([
        { nodeId: null, displayName: '总览' },
    ]);
    const [cameraPreset, setCameraPreset] = useState<CameraPreset>(L0_OVERVIEW_PRESET);
    const coreModelLinkIds = useMemo(() => Object.keys(PART_METADATA), []);

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
    const selectedCoreDetailRecord = useMemo(
        () => (selectedPart ? getCorePartDetailRecord(selectedPart.name) : null),
        [selectedPart],
    );
    const selectedDetailRecord = useMemo(
        () => (selectedDetailSelection ? getDetailPartDetailRecord(selectedDetailSelection) : null),
        [selectedDetailSelection],
    );
    const partInspectorLink = useMemo(
        () => selectedDetailSelection?.linkName ?? selectedPart?.name ?? null,
        [selectedDetailSelection, selectedPart],
    );
    const adjudicatedDisassemblyReady = Boolean(selectedScrewId && selectedToolId);
    const activeDetailRecord = selectedDetailRecord ?? selectedCoreDetailRecord;
    const hoveredDetailRecord = useMemo(
        () => (hoveredDetailSelection ? getDetailPartDetailRecord(hoveredDetailSelection) : null),
        [hoveredDetailSelection],
    );
    const corePartQuickSelectOptions = useMemo(() => ([
        {
            label: '上半身核心件',
            options: UPPER_BODY_CORE_LINKS.map((linkName) => ({
                value: linkName,
                label: PART_METADATA[linkName]?.displayName ?? getLinkDisplayName(linkName),
            })),
        },
        {
            label: '下半身与底座核心件',
            options: REMAINING_CORE_LINKS.map((linkName) => ({
                value: linkName,
                label: PART_METADATA[linkName]?.displayName ?? getLinkDisplayName(linkName),
            })),
        },
    ]), []);
    const diagnosisSnapshot = useMemo(() => readLatestDiagnosisResult(), []);
    const latestDiagnosisTraceId = diagnosisSnapshot?.traceId;

    const handleDiagnosisAction = useCallback(async (action: DiagnosisActionType) => {
        if (!latestDiagnosisTraceId || diagnosisActionLoading) {
            if (!latestDiagnosisTraceId) {
                message.error('当前没有可操作的诊断轨迹');
            }
            return;
        }

        setDiagnosisActionLoading(true);
        try {
            const response = await runDiagnosisAction(latestDiagnosisTraceId, action);
            if (action === 'escalate_to_teacher') {
                message.info(response.message);
            } else {
                message.success(response.message);
            }
        } catch (error: unknown) {
            const err = error as Error;
            message.error(err.message || '诊断动作执行失败');
        } finally {
            setDiagnosisActionLoading(false);
        }
    }, [diagnosisActionLoading, latestDiagnosisTraceId]);
    const viewerModelScale = viewState === 'ISOLATED'
        ? (selectedOverviewNode ? (ISOLATION_MODEL_SCALE_OVERRIDES[selectedOverviewNode] ?? 1.15) : 1.15)
        : 2;

    useEffect(() => {
        const unsubscribe = scoringEngine.subscribe((state) => {
            setScoreState(state);
        });
        return unsubscribe;
    }, []);

    // 预加载爆炸图子零件 GLB（静默后台）
    useEffect(() => {
        preloadAllParts();
    }, []);

    // 监听全屏变化事件（ESC 退出时同步状态）
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener('fullscreenchange', handleFullscreenChange);
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
    }, []);

    const toggleFullscreen = useCallback(() => {
        if (!viewerContainerRef.current) return;
        if (!document.fullscreenElement) {
            viewerContainerRef.current.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }, []);

    // 全屏态提升信息密度：保持隔离语义，提升展开幅度与可读性。
    useEffect(() => {
        if (isFullscreen && viewState === 'ISOLATED' && viewMode === 'explode') {
            setExplodeAmount((prev) => Math.max(prev, 0.35));
        }
    }, [isFullscreen, viewState, viewMode]);

    useEffect(() => {
        if (operationMode !== 'exam' || examSummaryReport) {
            examEndAtRef.current = null;
            return;
        }
        if (!examEndAtRef.current) {
            examEndAtRef.current = Date.now() + examRemainingMs;
        }
        const timer = setInterval(() => {
            if (!examEndAtRef.current) return;
            const remaining = Math.max(0, examEndAtRef.current - Date.now());
            setExamRemainingMs(remaining);
        }, 1000);
        return () => clearInterval(timer);
    }, [operationMode, examSummaryReport, examRemainingMs]);
    const runtimeSopScript = useMemo(() => {
        if (workspaceVariant === 'atom01' || !runtimeDraft) {
            return null;
        }
        return buildRuntimeSopScript(runtimeDraft);
    }, [runtimeDraft, workspaceVariant]);
    const availableSopScripts = useMemo(() => {
        if (!runtimeSopScript) {
            return ALL_SOP_SCRIPTS;
        }
        return [runtimeSopScript];
    }, [runtimeSopScript]);
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
    const activeSopScript = useMemo(() => {
        const targetSopId = linkedSOPId ?? sopSceneSync.state.selectedSopId;
        return availableSopScripts.find((sop) => sop.sopId === targetSopId) ?? availableSopScripts[0];
    }, [availableSopScripts, linkedSOPId, sopSceneSync.state.selectedSopId]);

    const handleSummarize = useCallback((report: AdjudicationReport) => {
        setExamSummaryReport(report);
        examEndAtRef.current = null;
    }, []);

    const handleResetExam = useCallback(() => {
        scoringEngine.reset(100);
        setExamSummaryReport(null);
        sopExecutor?.reset();
        setExamRemainingMs(EXAM_DURATION_MS);
        examEndAtRef.current = operationMode === 'exam' ? Date.now() + EXAM_DURATION_MS : null;
    }, [sopExecutor, operationMode]);

    const applyRuntimeDraft = useCallback((draft: MaintenanceDraftResponse) => {
        const manifest = createRuntimeManifestAdapter(draft);
        setRuntimeDraft(draft);
        setRuntimeManifest(manifest);
        const firstTarget = draft.draft.steps[0]?.model_targets ?? [];
        setRuntimeTargetIds(firstTarget);
        setRuntimeSelectedAssetPath(resolveRuntimeAssetPaths(manifest, firstTarget)[0] ?? manifest.parts[0] ?? null);
        setLinkedSOPId(`runtime-${draft.draft_id}`);
        setRightPanelTab('part');
    }, []);

    useEffect(() => {
        if (workspaceVariant === 'atom01') {
            setRuntimeWorkspaceSession(null);
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

        setRuntimeWorkspaceSession(session);
        if (session.draft) {
            applyRuntimeDraft(session.draft);
        }
    }, [applyRuntimeDraft, workspaceVariant]);

    const handlePartHover = useCallback((part: PartInfo | null) => {
        if (part) {
            setHoveredDetailSelection(null);
        }
        setHoveredPart(part);
    }, []);

    const emitSOPActionEvent = useCallback((event: Omit<SOPActionEvent, 'seq'>) => {
        sopActionSeqRef.current += 1;
        setSopActionEvent({
            seq: sopActionSeqRef.current,
            ...event,
        });
    }, []);

    // Gate-1: 进入 L1 隔离态
    const enterIsolation = useCallback((overviewNodeId: string) => {
        lastAutoCameraSignatureRef.current = '';
        setViewState('ISOLATED');
        setIsolationLevel(1);
        setSelectedOverviewNode(overviewNodeId);
        const displayName = PART_METADATA[overviewNodeId]?.displayName ?? getLinkDisplayName(overviewNodeId);
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
    }, []);

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

    const handleCorePartQuickSelect = useCallback((linkName: string) => {
        enterIsolation(linkName);
    }, [enterIsolation]);

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
    }, [viewState, enterIsolation, enterL2, emitSOPActionEvent]);

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
    }, [l2SelectedPartIdx, emitSOPActionEvent]);

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

    const handleScrewSelect = useCallback((screwId: string) => {
        setSelectedScrewId(screwId);
        setRightPanelTab('tool');
        emitSOPActionEvent({
            type: 'screw_selected',
            screwId,
        });
    }, [emitSOPActionEvent]);

    const applySOPIntent = useCallback((intent: { targetPart: string | null; explodeAmount: number; requiredTool: string | null }) => {
        if (intent.requiredTool) {
            setSelectedToolId(intent.requiredTool);
            setCurrentTool(intent.requiredTool);
        }

        if (intent.targetPart) {
            const part = PART_METADATA[intent.targetPart];
            if (part) {
                if (viewState === 'OVERVIEW' || selectedOverviewNode !== intent.targetPart) {
                    enterIsolation(intent.targetPart);
                }
                setSelectedPart(part);
                setRightPanelTab('part');
            }
        }

        if (intent.explodeAmount > 0) {
            setViewMode('explode');
            setExplodeAmount(Math.max(intent.explodeAmount, 0.25));
        }
    }, [setCurrentTool, viewState, selectedOverviewNode, enterIsolation]);

    // SOP 播放器回调
    const handleSOPPartSelect = useCallback((partName: string | null) => {
        if (runtimeManifest) {
            const targetIds = partName ? [partName] : [];
            setRuntimeTargetIds(targetIds);
            const assetPaths = resolveRuntimeAssetPaths(runtimeManifest, targetIds);
            setRuntimeSelectedAssetPath(assetPaths[0] ?? runtimeManifest.parts[0] ?? null);
        }
        if (partName) {
            const part = PART_METADATA[partName];
            if (part) {
                if (viewState === 'OVERVIEW' || selectedOverviewNode !== partName) {
                    enterIsolation(partName);
                }
                setSelectedPart(part);
                setRightPanelTab('part');
            }
        } else {
            setSelectedPart(null);
        }
    }, [runtimeManifest, viewState, selectedOverviewNode, enterIsolation]);

    const handleSOPToolRequired = useCallback((toolId: string | null) => {
        if (toolId) setSelectedToolId(toolId);
        setCurrentTool(toolId ?? null);
    }, [setCurrentTool]);

    const handleSOPChange = useCallback((sop: SOPScriptAdjudication | null) => {
        setLinkedSOPId(sop?.sopId ?? null);
        setSelectedScrewId(null);
        setSelectedToolId(null);
        setCurrentTool(null);
        resetToOverview();
        const intent = sopSceneSync.bindSOP(sop);
        if (intent) {
            applySOPIntent(intent);
        }
    }, [setCurrentTool, resetToOverview, sopSceneSync, applySOPIntent]);

    const handleSOPStepChange = useCallback((step: SOPStepAdjudication | null, index: number) => {
        const intent = sopSceneSync.bindStep(step, index);
        applySOPIntent(intent);
        if (runtimeManifest) {
            const targetIds = step?.targetParts ?? [];
            setRuntimeTargetIds(targetIds);
            const assetPaths = resolveRuntimeAssetPaths(runtimeManifest, targetIds);
            setRuntimeSelectedAssetPath(assetPaths[0] ?? runtimeManifest.parts[0] ?? null);
        }
        if (step && /收起|恢复正常|复位/.test(`${step.title} ${step.description}`)) {
            setExplodeAmount(0);
        }
    }, [runtimeManifest, sopSceneSync, applySOPIntent]);

    const handleSOPContextChange = useCallback((context: SOPExecutionContext | null, _step: SOPStepAdjudication | null) => {
        sopSceneSync.bindContext(context);
        if (context?.executionState === SOPExecutionState.COMPLETE) {
            setExplodeAmount(0);
        }
    }, [sopSceneSync]);

    const handleSOPBlocked = useCallback((report: AdjudicationReport) => {
        sopSceneSync.bindBlocked(report);
        setRightPanelTab('part');
    }, [sopSceneSync]);

    // 双击聚焦
    const handlePartDoubleClick = useCallback((part: PartInfo) => {
        setFocusTarget(part.name);
        setTimeout(() => setFocusTarget(null), 100);
    }, []);

    const handleVisibleBoundsChange = useCallback((bounds: { center: [number, number, number]; radius: number }) => {
        if (viewState !== 'ISOLATED') return;
        const [cx, cy, cz] = bounds.center;
        if (![cx, cy, cz].every(Number.isFinite)) return;

        const radius = Math.min(Math.max(bounds.radius, 0.08), 1.15);
        const isTorso = selectedOverviewNode === 'torso_link';
        const isUpperLimb = selectedOverviewNode ? /(arm|elbow)/.test(selectedOverviewNode) : false;
        const levelFactor = isTorso
            ? (isolationLevel >= 2 ? 1.85 : 2.05)
            : isUpperLimb
                ? (isolationLevel >= 2 ? 1.65 : 1.85)
                : (isolationLevel >= 2 ? 1.35 : 1.55);
        const fullscreenFactor = isFullscreen ? 0.9 : 1;
        const torsoFactor = isTorso ? 1.2 : 1;
        const maxDistance = isTorso ? 2.5 : (isUpperLimb ? 2.0 : 1.8);
        const distance = Math.min(Math.max(radius * levelFactor * fullscreenFactor * torsoFactor, 0.42), maxDistance);
        const nextPreset: CameraPreset = {
            position: [cx + distance, cy + distance * 0.45, cz + distance * 0.88],
            target: [cx, cy, cz],
            fov: selectedOverviewNode === 'torso_link' ? 52 : (isolationLevel >= 2 ? 44 : 48),
        };

        const signature = `${nextPreset.position.map(v => v.toFixed(3)).join(',')}|${nextPreset.target.map(v => v.toFixed(3)).join(',')}|${nextPreset.fov}`;
        if (signature === lastAutoCameraSignatureRef.current) return;
        lastAutoCameraSignatureRef.current = signature;
        setCameraPreset(nextPreset);
    }, [viewState, isolationLevel, isFullscreen, selectedOverviewNode]);

    // 获取当前零件的所有同组零件
    const getGroupParts = (group: string) => {
        return Object.values(PART_METADATA).filter(p => p.group === group);
    };

    const headerViewModeControl = (
        <Segmented
            aria-label="视图模式切换"
            value={viewMode}
            onChange={v => {
                const nextMode = v as typeof viewMode;
                if (nextMode === 'explode' && viewState !== 'ISOLATED') {
                    message.info('请先在总览中点击一个大部件，再进入爆炸图。');
                    setViewMode('normal');
                    setExplodeAmount(0);
                    return;
                }
                setViewMode(nextMode);
                if (nextMode === 'explode') {
                    setExplodeAmount(prev => Math.max(prev, EXPLODE_DEFAULT_ON_ENTER));
                } else if (nextMode === 'normal') {
                    resetToOverview();
                }
            }}
            options={[
                { label: <><EyeOutlined /> 正常</>, value: 'normal' },
                { label: <><ExpandOutlined /> 爆炸图</>, value: 'explode' },
            ]}
        />
    );

    const quickSelectControl = (
        <Select
            showSearch
            allowClear
            placeholder="下拉选择核心件"
            value={viewState === 'ISOLATED' ? selectedOverviewNode ?? undefined : undefined}
            options={corePartQuickSelectOptions}
            onChange={(value) => {
                if (value) {
                    handleCorePartQuickSelect(value);
                }
            }}
            onClear={resetToOverview}
            filterOption={(input, option) => String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
    );

    const diagnosisContent = (
        <DiagnosisPanel
            diagnosisResult={diagnosisSnapshot?.diagnosisResult ?? null}
            maintenancePlan={diagnosisSnapshot?.maintenancePlan ?? null}
            verificationResult={diagnosisSnapshot?.verificationResult ?? null}
            isLoading={false}
            isActionSubmitting={diagnosisActionLoading}
            onConfirmExecution={() => {
                void handleDiagnosisAction('confirm_execution');
            }}
            onEscalateToTeacher={() => {
                void handleDiagnosisAction('escalate_to_teacher');
            }}
        />
    );

    const partPanel = (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Card size="small" title={<><InfoCircleOutlined /> 零件详情</>}>
                {activeDetailRecord ? (
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <div style={{ textAlign: 'center', padding: '8px 0' }}>
                            <Title level={4} style={{ margin: 0 }}>
                                {activeDetailRecord.displayName}
                            </Title>
                            <Tag color={activeDetailRecord.level === 'core' ? 'blue' : 'geekblue'} style={{ marginTop: 8 }}>
                                {activeDetailRecord.level === 'core' ? '核心零件' : '细节零件'} · {activeDetailRecord.categoryLabel}
                            </Tag>
                        </div>

                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="零件 ID">
                                <Text code>{activeDetailRecord.id}</Text>
                            </Descriptions.Item>
                            <Descriptions.Item label="所属总成">
                                {activeDetailRecord.parentDisplayName}
                            </Descriptions.Item>
                            {activeDetailRecord.jointName && (
                                <Descriptions.Item label="关联关节">
                                    <Text code>{activeDetailRecord.jointName}</Text>
                                </Descriptions.Item>
                            )}
                            <Descriptions.Item label="模型路径">
                                <Text code style={{ fontSize: 11 }}>{activeDetailRecord.modelPath}</Text>
                            </Descriptions.Item>
                        </Descriptions>

                        <Text type="secondary" style={{ fontSize: 12 }}>
                            {activeDetailRecord.summary}
                        </Text>
                        <div style={{ padding: '8px 10px', borderRadius: 6, background: 'rgba(24, 144, 255, 0.08)' }}>
                            <Text strong style={{ fontSize: 12 }}>维保要点</Text>
                            <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                                {activeDetailRecord.maintenancePoints.map((point) => (
                                    <Text key={point} style={{ fontSize: 12 }}>
                                        • {point}
                                    </Text>
                                ))}
                            </div>
                        </div>

                        {activeDetailRecord.level === 'core' && (
                            <Button
                                type="default"
                                block
                                size="small"
                                onClick={() => setSelectedPart(null)}
                            >
                                取消选中
                            </Button>
                        )}
                    </Space>
                ) : (
                    <Empty
                        description="点击零件查看详情"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                )}
            </Card>

            {selectedPart && (
                <Card
                    size="small"
                    title={`${GROUP_NAMES[selectedPart.group]} 零件列表`}
                >
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {getGroupParts(selectedPart.group).map(part => (
                            <div
                                key={part.name}
                                style={{
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    cursor: 'pointer',
                                    background: part.name === selectedPart.name
                                        ? 'rgba(24, 144, 255, 0.2)'
                                        : 'transparent',
                                    border: part.name === selectedPart.name
                                        ? '1px solid #1890ff'
                                        : '1px solid transparent',
                                }}
                                onClick={() => setSelectedPart(part)}
                            >
                                <Text>{part.displayName}</Text>
                            </div>
                        ))}
                    </Space>
                </Card>
            )}

            <Card
                size="small"
                title="🧪 小件 3D 检视"
                extra={partInspectorLink ? <Tag color="cyan">已接入独立检视器</Tag> : null}
            >
                <PartInspector
                    selectedLink={partInspectorLink}
                    showFasteners={Boolean(selectedScrewId)}
                />
            </Card>

            {isolationLevel >= 2 && l2TargetLink && (
                <Card
                    size="small"
                    title={`📋 ${getLinkDisplayName(l2TargetLink)} 子零件列表`}
                >
                    <Space direction="vertical" style={{ width: '100%' }} size="small">
                        <Text type="secondary" style={{ fontSize: 12 }}>
                            小件可通过列表快速定位并高亮（代理点击）
                        </Text>
                        <div style={{ maxHeight: 180, overflowY: 'auto' }}>
                            {l2DetailParts.map((part, idx) => (
                                <div
                                    key={`${l2TargetLink}-list-${idx}`}
                                    style={{
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        padding: '4px 8px',
                                        marginBottom: 4,
                                        borderRadius: 4,
                                        cursor: 'pointer',
                                        border: l2SelectedPartIdx === idx ? '1px solid #40a9ff' : '1px solid transparent',
                                        background: l2SelectedPartIdx === idx ? 'rgba(64, 169, 255, 0.15)' : 'rgba(255,255,255,0.02)',
                                    }}
                                    onClick={() => handleSubPartSelect(l2TargetLink, idx, part)}
                                >
                                    <Text style={{ fontSize: 12 }}>{part.displayName}</Text>
                                    <Tag color="blue" style={{ marginRight: 0 }}>代理</Tag>
                                </div>
                            ))}
                        </div>
                    </Space>
                </Card>
            )}
        </Space>
    );

    const leftRailIsolationControls = viewState === 'ISOLATED' && isolationSets ? (
        <Card size="small" title="🧩 当前部位子组件">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Text type="secondary" style={{ fontSize: 12 }}>
                    点击子组件可直接进入下钻，避免在拥挤视图中盲点。
                </Text>
                {isolationSets.targetLinks.map((linkName) => {
                    const isCurrent = l2TargetLink === linkName;
                    return (
                        <Button
                            key={`link-entry-${linkName}`}
                            size="small"
                            type={isCurrent ? 'primary' : 'default'}
                            block
                            onClick={() => {
                                const part = PART_METADATA[linkName];
                                if (part) {
                                    handlePartSelect(part);
                                    return;
                                }
                                if (linkHasDetailParts(linkName)) {
                                    enterL2(linkName);
                                }
                            }}
                        >
                            {getLinkDisplayName(linkName)}
                        </Button>
                    );
                })}
            </Space>
        </Card>
    ) : null;

    const leftRailSopListContent = (
        <Card
            size="small"
            title="📚 SOP 列表"
            extra={(
                <Button
                    size="small"
                    type="text"
                    onClick={() => setIsSopListExpanded((prev) => !prev)}
                >
                    {isSopListExpanded ? '收起 SOP 列表' : '展开 SOP 列表'}
                </Button>
            )}
        >
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Text type="secondary" style={{ fontSize: 12 }}>
                    默认收起，避免打断执行；展开后可切换到其他 SOP。
                </Text>
                {isSopListExpanded ? availableSopScripts.map((sop) => {
                    const isActive = sop.sopId === linkedSOPId;
                    return (
                        <Button
                            key={`sop-link-${sop.sopId}`}
                            size="small"
                            type={isActive ? 'primary' : 'default'}
                            block
                            onClick={() => setLinkedSOPId(sop.sopId)}
                        >
                            {sop.title}
                        </Button>
                    );
                }) : null}
                {sopSceneSync.state.selectedSopId && (
                    <div style={{ padding: '8px 10px', borderRadius: 6, background: 'rgba(24, 144, 255, 0.08)' }}>
                        <Space wrap>
                            <Tag color="blue" style={{ margin: 0 }}>{sopSceneSync.state.selectedSopTitle}</Tag>
                            <Tag color="cyan" style={{ margin: 0 }}>步骤 {sopSceneSync.progressText}</Tag>
                            {sopSceneSync.state.executionState && (
                                <Tag
                                    color={SOP_EXECUTION_STATE_TAG_COLOR[sopSceneSync.state.executionState] ?? 'default'}
                                    style={{ margin: 0 }}
                                >
                                    {SOP_EXECUTION_STATE_LABEL[sopSceneSync.state.executionState]}
                                </Tag>
                            )}
                        </Space>
                        {sopSceneSync.state.currentStepTitle && (
                            <Text style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
                                当前步骤：{sopSceneSync.state.currentStepTitle}
                            </Text>
                        )}
                        {sopSceneSync.state.blockedReason && (
                            <Text type="danger" style={{ display: 'block', marginTop: 4, fontSize: 12 }}>
                                阻断原因：{sopSceneSync.state.blockedReason}
                            </Text>
                        )}
                    </div>
                )}
            </Space>
        </Card>
    );

    const leftRailToolSelectorContent = (
        <ToolSelector
            selectedToolId={selectedToolId}
            onToolSelect={(toolId) => {
                setSelectedToolId(toolId);
                setCurrentTool(toolId);
                emitSOPActionEvent({
                    type: 'tool_selected',
                    toolId,
                });
            }}
            requiredScrewId={selectedScrewId || undefined}
        />
    );

    const leftRailSopPlayerContent = (
        <SOPPlayerAdjudicated
            availableSOPs={availableSopScripts}
            selectedSOPId={linkedSOPId}
            onSOPChange={handleSOPChange}
            onStepChange={handleSOPStepChange}
            onExecutionContextChange={handleSOPContextChange}
            onBlocked={handleSOPBlocked}
            onExplodeChange={setExplodeAmount}
            onPartSelect={handleSOPPartSelect}
            onToolRequired={handleSOPToolRequired}
            currentToolId={selectedToolId}
            actionEvent={sopActionEvent}
            onSummarize={handleSummarize}
            onExecutorReady={setSopExecutor}
        />
    );

    const workspaceSwitcherCard = workspaceVariant === 'runtime' ? (
        <Card size="small">
            <div style={{ display: 'grid', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                    <div style={{ display: 'grid', gap: 4 }}>
                        <Text strong>
                            {effectiveLayoutMode === 'execution'
                                ? '执行页仅保留步骤、工具、播放器与 3D 操作区'
                                : '检视页聚焦诊断、部件定位与维保详情'}
                        </Text>
                        <Text type="secondary">
                            {effectiveLayoutMode === 'execution'
                                ? '分析信息已迁移到独立检视页，减少执行中断。'
                                : '执行步骤与工具操作保留在独立执行页，便于专注完成 SOP。'}
                        </Text>
                    </div>
                    <Space wrap>
                        <Button onClick={() => navigate('/maintenance/project-draft')}>
                            项目草案页
                        </Button>
                        <Button
                            type={effectiveLayoutMode === 'execution' ? 'primary' : 'default'}
                            onClick={() => navigate(effectiveLayoutMode === 'execution' ? '/maintenance/inspector' : '/maintenance')}
                        >
                            {effectiveLayoutMode === 'execution' ? '打开检视页' : '返回执行页'}
                        </Button>
                    </Space>
                </div>

                {runtimeWorkspaceSession ? (
                    <Descriptions size="small" column={4} bordered>
                        <Descriptions.Item label="当前项目">
                            {runtimeWorkspaceSession.projectLabel ?? runtimeWorkspaceSession.projectId ?? '未选择'}
                        </Descriptions.Item>
                        <Descriptions.Item label="维保目标">
                            {runtimeWorkspaceSession.maintenanceGoal || '执行器弯曲维护'}
                        </Descriptions.Item>
                        <Descriptions.Item label="关注部位">
                            {runtimeWorkspaceSession.focusArea || '肘关节'}
                        </Descriptions.Item>
                        <Descriptions.Item label="当前草案">
                            {runtimeDraft?.draft.title ?? '尚未加载'}
                        </Descriptions.Item>
                    </Descriptions>
                ) : null}

                {runtimeDraft && runtimeManifest?.parts.length ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                        <Text strong>当前运行时模型资源</Text>
                        <Space wrap>
                            {(runtimeManifest.parts ?? []).map((assetPath) => (
                                <Button
                                    key={assetPath}
                                    size="small"
                                    type={runtimeSelectedAssetPath === assetPath ? 'primary' : 'default'}
                                    onClick={() => setRuntimeSelectedAssetPath(assetPath)}
                                >
                                    {assetPath}
                                </Button>
                            ))}
                        </Space>
                    </div>
                ) : null}

                {runtimeManifest?.reviewWarnings.length ? (
                    <Alert
                        type="warning"
                        showIcon
                        message={runtimeManifest.reviewWarnings.join('；')}
                    />
                ) : null}
            </div>
        </Card>
    ) : null;

    return (
        <div className="flex h-[calc(100vh-120px)] flex-col gap-4">
            <SOPMaintenanceHeader
                viewModeControl={headerViewModeControl}
                title={workspaceChrome.title}
                subtitle={workspaceChrome.subtitle}
                breadcrumb={workspaceChrome.breadcrumb}
            />

            {workspaceChrome.showDraftEntry ? workspaceSwitcherCard : null}

            <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
                {showExecutionRail ? (
                    <Col xs={24} lg={effectiveLayoutMode === 'full' ? 6 : 8} style={{ height: '100%', overflowY: 'auto' }}>
                        <SOPMaintenanceLeftRail
                            sopTitle={activeSopScript?.title ?? 'SOP 步骤导航'}
                            difficultyLabel={activeSopScript?.difficulty ?? 'normal'}
                            currentStepTitle={sopSceneSync.state.currentStepTitle}
                            steps={(activeSopScript?.steps ?? []).map((step) => ({
                                stepId: step.stepId,
                                title: step.title,
                                description: step.description,
                                onFailureAction: step.onFailure?.action,
                                hasCriticalFailureReason: step.failureReasons?.some((reason) => reason.severity === 'critical') ?? false,
                            }))}
                            isolationControls={leftRailIsolationControls}
                            sopListContent={leftRailSopListContent}
                            toolSelectorContent={leftRailToolSelectorContent}
                            sopPlayerContent={leftRailSopPlayerContent}
                        />
                    </Col>
                ) : null}

                <Col
                    xs={24}
                    lg={isFullscreen ? 24 : effectiveLayoutMode === 'full' ? 12 : 16}
                    style={{ height: '100%' }}
                >
                    <div
                        ref={viewerContainerRef}
                        role="region"
                        aria-label="SOP 3D 视图区"
                        style={{ height: '100%', background: '#0a1929' }}
                    >
                        <Card
                            size="small"
                            style={{ height: '100%' }}
                            styles={{
                                body: {
                                    height: 'calc(100% - 40px)',
                                    padding: 0,
                                    background: '#0a1929',
                                    borderRadius: '0 0 8px 8px',
                                },
                            }}
                            title={
                                <Space size={4} style={{ fontSize: 14 }}>
                                    {breadcrumbPath.map((item, idx) => (
                                        <span key={idx} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                            {idx > 0 && <RightOutlined style={{ fontSize: 10, color: '#8b949e' }} />}
                                            <span
                                                style={{
                                                    cursor: idx < breadcrumbPath.length - 1 ? 'pointer' : 'default',
                                                    color: idx < breadcrumbPath.length - 1 ? '#58a6ff' : '#e6edf3',
                                                    fontWeight: idx === breadcrumbPath.length - 1 ? 600 : 400,
                                                }}
                                                onClick={() => {
                                                    navigateBreadcrumb(idx);
                                                }}
                                            >
                                                {idx === 0 && <HomeOutlined style={{ marginRight: 4 }} />}
                                                {item.displayName}
                                            </span>
                                        </span>
                                    ))}
                                </Space>
                            }
                            extra={
                                <Space>
                                    {viewState === 'ISOLATED' && (
                                        <Button
                                            size="small"
                                            type="link"
                                            onClick={resetToOverview}
                                            style={{ color: '#58a6ff', padding: '0 4px' }}
                                        >
                                            ↩ 返回总览
                                        </Button>
                                    )}
                                    {viewState === 'ISOLATED' && UI_CAPABILITIES.allow_toggle_fade_hide && (
                                        <Button
                                            size="small"
                                            type="text"
                                            onClick={() => setSiblingsMode(prev => prev === 'fade' ? 'hide' : 'fade')}
                                            style={{ color: '#c9d1d9' }}
                                        >
                                            {siblingsMode === 'fade' ? '同级：淡出' : '同级：隐藏'}
                                        </Button>
                                    )}
                                    {isFullscreen && (
                                        <Tag color="cyan">全屏增强</Tag>
                                    )}
                                    {hoveredDetailRecord && (
                                        <Tag color="cyan">{hoveredDetailRecord.displayName}</Tag>
                                    )}
                                    {!hoveredDetailRecord && hoveredPart && (
                                        <Tag color="cyan">{hoveredPart.displayName}</Tag>
                                    )}
                                    {selectedPart && (
                                        <Tag color="blue">{selectedPart.displayName}</Tag>
                                    )}
                                    {UI_CAPABILITIES.allow_fullscreen && (
                                        <Button
                                            type="text"
                                            size="small"
                                            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                                            onClick={toggleFullscreen}
                                            title={isFullscreen ? '退出全屏' : '全屏'}
                                            style={{ color: '#e6edf3' }}
                                        />
                                    )}
                                </Space>
                            }
                        >
                            <Canvas
                                key={`cam-${cameraPreset.position.join(',')}-${cameraPreset.target.join(',')}-${cameraPreset.fov}`}
                                camera={{ position: cameraPreset.position, fov: cameraPreset.fov }}
                                shadows
                                dpr={[1, 2]}
                            >
                                <ambientLight intensity={0.5} />
                                <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
                                <directionalLight position={[-5, 3, -5]} intensity={0.4} />

                                <color attach="background" args={['#0a1929']} />

                                <gridHelper args={[3, 30, '#1e3a5f', '#1e3a5f']} position={[0, -0.8, 0]} />

                                {/* 摄像机聚焦控制器 */}
                                <CameraController focusTarget={focusTarget} />

                                <Suspense fallback={<LoadingFallback />}>
                                    {runtimeManifest ? (
                                        <RuntimeAssetPreview assetUrl={runtimePreviewAssetUrl} assetPath={runtimePreviewAssetPath} />
                                    ) : (
                                        <>
                                            <Atom01Interactive
                                                scale={viewerModelScale}
                                                position={[0, 0.5, 0]}
                                                explodeAmount={effectiveExplodeAmount}
                                                showSubParts={viewState === 'ISOLATED' && viewMode === 'explode'}
                                                visiblePartNames={visibleLinks}
                                                clickablePartNames={clickableLinks}
                                                referencePartNames={referenceLinks}
                                                preserveReferenceInExplode={true}
                                                fadedPartNames={fadedLinks}
                                                fadeOpacity={isFullscreen ? 0.12 : 0.15}
                                                onPartHover={handlePartHover}
                                                onPartSelect={handlePartSelect}
                                                onPartDoubleClick={handlePartDoubleClick}
                                                hoveredPart={hoveredPart?.name}
                                                selectedPart={selectedPart?.name}
                                                isolationLevel={isolationLevel}
                                                l2TargetLink={l2TargetLink}
                                                l2SelectedPartIdx={l2SelectedPartIdx}
                                                onSubPartSelect={handleSubPartSelect}
                                                onSubPartHover={handleSubPartHover}
                                                subPartEnabledNames={subPartEnabledLinks}
                                                fullscreenMode={isFullscreen}
                                                onVisibleBoundsChange={handleVisibleBoundsChange}
                                            />
                                            <DetailParts
                                                selectedLink={selectedPart?.name ?? null}
                                                visible={showDetailParts}
                                            />
                                        </>
                                    )}
                                </Suspense>

                                {/* 拆卸动画演示 */}
                                {adjudicatedDisassemblyReady && selectedScrewId ? (
                                    <DisassemblyDemoAdjudicated
                                        isPlaying={disassemblyPlaying}
                                        screwId={selectedScrewId}
                                        toolId={selectedToolId ?? undefined}
                                        onAnimationRollback={() => {
                                            setDisassemblyStep('↩ 裁决阻断，动画已回滚');
                                        }}
                                        onAdjudicationBlocked={(report) => {
                                            setDisassemblyStep(`⛔ 裁决阻断：${report.reasonCode}`);
                                            message.error(`拆卸被阻断：${report.reasonCode}`);
                                            setDisassemblyPlaying(false);
                                        }}
                                        onAdjudicationComplete={() => {
                                            setDisassemblyPlaying(false);
                                            setDisassemblyStep('✅ 裁决通过，已提交拆卸状态');
                                            message.success('拆卸裁决通过');
                                        }}
                                    />
                                ) : (
                                    <DisassemblyAnimation
                                        isPlaying={disassemblyPlaying}
                                        onCurrentStep={setDisassemblyStep}
                                        onExplodeAmountChange={setExplodeAmount}
                                        onComplete={() => {
                                            setDisassemblyPlaying(false);
                                            message.success('拆卸动画播放完成');
                                        }}
                                    />
                                )}

                                <OrbitControls
                                    key={`orbit-${viewState}-${selectedOverviewNode}`}
                                    enablePan={true}
                                    enableZoom={true}
                                    enableRotate={true}
                                    minDistance={0.5}
                                    maxDistance={5}
                                    target={cameraPreset.target}
                                />
                            </Canvas>
                        </Card>
                    </div>
                </Col>

                {showInspectorRail ? (
                    <Col xs={24} lg={effectiveLayoutMode === 'full' ? 6 : 8} style={{ height: '100%', overflowY: 'auto' }}>
                        <SOPMaintenanceRightRail
                            rightPanelTab={rightPanelTab}
                            onRightPanelTabChange={setRightPanelTab}
                            quickSelectControl={quickSelectControl}
                            diagnosisContent={diagnosisContent}
                            partPanel={partPanel}
                            screwPanel={(
                                <ScrewInfo
                                    partName={selectedPart?.name || null}
                                    detailSelection={selectedDetailSelection}
                                    onScrewSelect={handleScrewSelect}
                                    selectedScrewId={selectedScrewId}
                                />
                            )}
                        />
                    </Col>
                ) : null}
            </Row>

            {/* 考试结束覆盖层 */}
            {examSummaryReport && (
                <SOPMaintenanceExamOverlay
                    reasonCode={examSummaryReport.reasonCode}
                    currentScore={scoreState.currentScore}
                    onReset={handleResetExam}
                />
            )}
        </div>
    );
}

export default SOPMaintenancePage;
