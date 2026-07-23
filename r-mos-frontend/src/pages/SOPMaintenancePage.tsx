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

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button, Card, Col, Row, Segmented, Select, Space, Tag, message } from 'antd';
import {
    EyeOutlined,
    ExpandOutlined,
    FullscreenOutlined,
    FullscreenExitOutlined,
    HomeOutlined,
    RightOutlined,
} from '@ant-design/icons';
import { Canvas } from '@react-three/fiber';
import { useNavigate } from 'react-router-dom';
import { type DiagnosisActionType, runDiagnosisAction } from '@/api/agent-v2';
import { DiagnosisPanel, readLatestDiagnosisResult } from '@/components/DiagnosisPanel/DiagnosisPanel';
import { type PartInfo, buildPartMetadata } from '@/components/Viewer3D/manifestPartMetadata';
import { useAssemblyManifest } from '@/components/Viewer3D/useAssemblyManifest';
import {
    UI_CAPABILITIES,
} from '@/components/Viewer3D/partsManifest';
import { preloadOverviewParts } from '@/components/Viewer3D/ModelPreloader';
import {
    getLinkDisplayName,
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
import {
    getCorePartDetailRecord,
    getDetailPartDetailRecord,
} from '@/data/maintenanceKnowledge';
import {
    useAdjudicationStore,
    injectManifestPartRegistry,
    clearManifestPartRegistry,
} from '@/adjudication';
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';
import { useSOPSceneSync } from '@/adjudication/ui/useSOPSceneSync';
import { useRobotContextStore } from '@/store/robotContextStore';
import { useSOPScripts } from '@/hooks/useSOPScripts';
import {
    EXPLODE_DEFAULT_ON_ENTER,
    GROUP_NAMES,
    UPPER_BODY_CORE_LINKS,
    REMAINING_CORE_LINKS,
    buildLinkGroupsFromManifest,
    WORKSPACE_CHROME,
    type WorkspaceVariant,
    type MaintenanceLayoutMode,
} from './sopMaintenance/sopMaintenanceConfig';
import { useRuntimeDraft } from './sopMaintenance/useRuntimeDraft';
import { useSOPViewState } from './sopMaintenance/useSOPViewState';
import { useSOPPlaybackBridge } from './sopMaintenance/useSOPPlaybackBridge';
import {
    PartDetailPanel,
    LeftRailIsolationControls,
    LeftRailSopList,
} from './sopMaintenance/SOPMaintenancePanels';
import { SOPViewerScene } from './sopMaintenance/SOPViewerScene';
import { Viewer3DErrorBoundary } from '@/components/common/ErrorBoundary';

interface SOPMaintenancePageProps {
    workspaceVariant?: WorkspaceVariant;
    layoutMode?: MaintenanceLayoutMode;
}

function SOPMaintenancePage({ workspaceVariant = 'runtime', layoutMode }: SOPMaintenancePageProps) {
    const currentRobot = useRobotContextStore((s) => s.currentRobot);
    const { scripts: apiSopScripts } = useSOPScripts(currentRobot?.id);
    const robotId = currentRobot ? String(currentRobot.id) : null;
    const { manifest } = useAssemblyManifest(currentRobot?.id);

    useEffect(() => {
        const m = manifest as RobotDataManifest | null;
        if (m?.parts_registry) {
            injectManifestPartRegistry(m);
        }
        return () => { clearManifestPartRegistry(); };
    }, [manifest]);

    const manifestLinkGroups = useMemo(
        () => buildLinkGroupsFromManifest(manifest as any),
        [manifest]
    )
    const upperLinks = manifestLinkGroups?.upperLinks ?? UPPER_BODY_CORE_LINKS
    const lowerLinks = manifestLinkGroups?.lowerLinks ?? REMAINING_CORE_LINKS
    const groupNames = manifestLinkGroups?.groupNames ?? GROUP_NAMES
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const sopParam = searchParams.get('sop');
    const workspaceChrome = WORKSPACE_CHROME[workspaceVariant];
    const workspaceTitle = workspaceVariant === 'demo' && currentRobot
        ? `${currentRobot.model_name} 维保工作台`
        : workspaceChrome.title;
    const effectiveLayoutMode: MaintenanceLayoutMode = workspaceVariant === 'demo' ? 'full' : (layoutMode ?? 'execution');
    const showExecutionRail = effectiveLayoutMode !== 'inspector';
    const showInspectorRail = effectiveLayoutMode !== 'execution';
    const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
    const [linkedSOPId, setLinkedSOPId] = useState<string | null>(null);
    const [isSopListExpanded, setIsSopListExpanded] = useState(false);
    const [sopActionEvent, setSopActionEvent] = useState<SOPActionEvent | null>(null);
    const [selectedScrewId, setSelectedScrewId] = useState<string | null>(null);
    const [rightPanelTab, setRightPanelTab] = useState<string>('part');
    const [disassemblyPlaying, setDisassemblyPlaying] = useState(false);
    const [, setDisassemblyStep] = useState<string>('');
    const showDetailParts = false;
    const {
        runtimeManifest,
        setRuntimeTargetIds,
        setRuntimeSelectedAssetPath,
        runtimeSopScript,
        runtimePreviewAssetPath,
        runtimePreviewAssetUrl,
    } = useRuntimeDraft({ workspaceVariant, setLinkedSOPId, setRightPanelTab });
    const [diagnosisActionLoading, setDiagnosisActionLoading] = useState(false);
    const viewerContainerRef = useRef<HTMLDivElement>(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const sopActionSeqRef = useRef(0);
    const operationMode = useAdjudicationStore((state) => state.operationMode);
    const setCurrentTool = useAdjudicationStore((state) => state.setCurrentTool);
    const sopSceneSync = useSOPSceneSync();

    const partMetadata = useMemo((): Record<string, PartInfo> => {
        if (manifest) return buildPartMetadata(manifest);
        return {};
    }, [manifest]);

    const emitSOPActionEvent = useCallback((event: Omit<SOPActionEvent, 'seq'>) => {
        sopActionSeqRef.current += 1;
        setSopActionEvent({
            seq: sopActionSeqRef.current,
            ...event,
        });
    }, []);

    const {
        viewState,
        selectedOverviewNode,
        breadcrumbPath,
        cameraPreset,
        isolationLevel,
        l2TargetLink,
        l2SelectedPartIdx,
        siblingsMode,
        setSiblingsMode,
        setExplodeAmount,
        hoveredPart,
        selectedPart,
        setSelectedPart,
        viewMode,
        setViewMode,
        hoveredDetailSelection,
        focusTarget,
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
    } = useSOPViewState({
        partMetadata,
        emitSOPActionEvent,
        setSelectedScrewId,
        setRightPanelTab,
        isFullscreen,
        runtimeManifest,
    });

    const {
        examSummaryReport,
        scoreState,
        setSopExecutor,
        handleSummarize,
        handleResetExam,
        handleSOPPartSelect,
        handleSOPToolRequired,
        handleSOPChange,
        handleSOPStepChange,
        handleSOPContextChange,
        handleSOPBlocked,
    } = useSOPPlaybackBridge({
        operationMode,
        setCurrentTool,
        sopSceneSync,
        partMetadata,
        viewState,
        selectedOverviewNode,
        enterIsolation,
        resetToOverview,
        setSelectedPart,
        setViewMode,
        setExplodeAmount,
        runtimeManifest,
        setRuntimeTargetIds,
        setRuntimeSelectedAssetPath,
        setLinkedSOPId,
        setSelectedScrewId,
        setSelectedToolId,
        setRightPanelTab,
    });

    const selectedCoreDetailRecord = useMemo(
        () => (selectedPart ? getCorePartDetailRecord(selectedPart.name, robotId ?? undefined) : null),
        [selectedPart, robotId],
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
            options: upperLinks.map((linkName) => ({
                value: linkName,
                label: partMetadata[linkName]?.displayName ?? getLinkDisplayName(linkName),
            })),
        },
        {
            label: '下半身与底座核心件',
            options: lowerLinks.map((linkName) => ({
                value: linkName,
                label: partMetadata[linkName]?.displayName ?? getLinkDisplayName(linkName),
            })),
        },
    ]), [upperLinks, lowerLinks, partMetadata]);
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

    // 预加载概览级爆炸图子零件 GLB（静默后台）；明细零件由 DetailParts 按需加载
    useEffect(() => {
        preloadOverviewParts();
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

    const availableSopScripts = useMemo(() => {
        if (!runtimeSopScript) {
            return apiSopScripts;
        }
        return [runtimeSopScript];
    }, [runtimeSopScript, apiSopScripts]);
    const activeSopScript = useMemo(() => {
        const targetSopId = linkedSOPId ?? sopSceneSync.state.selectedSopId;
        return availableSopScripts.find((sop) => sop.sopId === targetSopId) ?? availableSopScripts[0];
    }, [availableSopScripts, linkedSOPId, sopSceneSync.state.selectedSopId]);

    const handleCorePartQuickSelect = useCallback((linkName: string) => {
        enterIsolation(linkName);
    }, [enterIsolation]);

    const handleScrewSelect = useCallback((screwId: string) => {
        setSelectedScrewId(screwId);
        setRightPanelTab('tool');
        emitSOPActionEvent({
            type: 'screw_selected',
            screwId,
        });
    }, [emitSOPActionEvent]);

    // 获取当前零件的所有同组零件
    const getGroupParts = (group: string) => {
        return Object.values(partMetadata).filter(p => p.group === group);
    };

    const headerViewModeControl = (
        <div className="flex flex-wrap items-center justify-end gap-2">
            {workspaceChrome.showDraftEntry ? (
                <Space wrap>
                    <Button onClick={() => navigate('/maintenance?view=project-draft')}>
                        项目草案页
                    </Button>
                    <Button
                        type={effectiveLayoutMode === 'execution' ? 'primary' : 'default'}
                        onClick={() => navigate(effectiveLayoutMode === 'execution' ? '/maintenance?view=inspector' : '/maintenance')}
                    >
                        {effectiveLayoutMode === 'execution' ? '打开检视页' : '返回执行页'}
                    </Button>
                </Space>
            ) : null}
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
        </div>
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
        <PartDetailPanel
            activeDetailRecord={activeDetailRecord}
            selectedPart={selectedPart}
            groupNames={groupNames}
            getGroupParts={getGroupParts}
            partInspectorLink={partInspectorLink}
            selectedScrewId={selectedScrewId}
            isolationLevel={isolationLevel}
            l2TargetLink={l2TargetLink}
            l2DetailParts={l2DetailParts}
            l2SelectedPartIdx={l2SelectedPartIdx}
            onSubPartSelect={handleSubPartSelect}
            onSelectPart={setSelectedPart}
        />
    );

    const leftRailIsolationControls = (
        <LeftRailIsolationControls
            viewState={viewState}
            isolationSets={isolationSets}
            l2TargetLink={l2TargetLink}
            partMetadata={partMetadata}
            onPartSelect={handlePartSelect}
            onEnterL2={enterL2}
        />
    );

    const leftRailSopListContent = (
        <LeftRailSopList
            isSopListExpanded={isSopListExpanded}
            onToggleExpanded={() => setIsSopListExpanded((prev) => !prev)}
            availableSopScripts={availableSopScripts}
            linkedSOPId={linkedSOPId}
            onSelectSop={setLinkedSOPId}
            sopSceneSync={sopSceneSync}
        />
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
            initialSopId={sopParam ?? undefined}
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

    return (
        <div className="flex h-[calc(100vh-120px)] flex-col gap-4">
            <SOPMaintenanceHeader
                viewModeControl={headerViewModeControl}
                title={workspaceTitle}
                breadcrumb={workspaceChrome.breadcrumb}
            />

            <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
                {showExecutionRail ? (
                    <Col xs={24} lg={effectiveLayoutMode === 'full' ? 6 : 8} style={{ height: '100%', overflowY: 'auto' }}>
                        <SOPMaintenanceLeftRail
                            robotModelName={currentRobot?.model_name}
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
                            <Viewer3DErrorBoundary>
                                <Canvas
                                    key={`cam-${cameraPreset.position.join(',')}-${cameraPreset.target.join(',')}-${cameraPreset.fov}`}
                                    camera={{ position: cameraPreset.position, fov: cameraPreset.fov }}
                                    shadows
                                    dpr={[1, 2]}
                                >
                                    <SOPViewerScene
                                        cameraPreset={cameraPreset}
                                        focusTarget={focusTarget}
                                        runtimeManifest={runtimeManifest}
                                        runtimePreviewAssetUrl={runtimePreviewAssetUrl}
                                        runtimePreviewAssetPath={runtimePreviewAssetPath}
                                        manifest={manifest}
                                        currentRobot={currentRobot}
                                        robotId={robotId}
                                        viewerModelScale={viewerModelScale}
                                        effectiveExplodeAmount={effectiveExplodeAmount}
                                        visibleLinks={visibleLinks}
                                        clickableLinks={clickableLinks}
                                        fadedLinks={fadedLinks}
                                        referenceLinks={referenceLinks}
                                        subPartEnabledLinks={subPartEnabledLinks}
                                        isFullscreen={isFullscreen}
                                        hoveredPart={hoveredPart}
                                        selectedPart={selectedPart}
                                        showDetailParts={showDetailParts}
                                        viewState={viewState}
                                        viewMode={viewMode}
                                        isolationLevel={isolationLevel}
                                        l2TargetLink={l2TargetLink}
                                        l2SelectedPartIdx={l2SelectedPartIdx}
                                        selectedOverviewNode={selectedOverviewNode}
                                        adjudicatedDisassemblyReady={adjudicatedDisassemblyReady}
                                        selectedScrewId={selectedScrewId}
                                        selectedToolId={selectedToolId}
                                        disassemblyPlaying={disassemblyPlaying}
                                        onPartHover={handlePartHover}
                                        onPartSelect={handlePartSelect}
                                        onPartDoubleClick={handlePartDoubleClick}
                                        onSubPartSelect={handleSubPartSelect}
                                        onSubPartHover={handleSubPartHover}
                                        onVisibleBoundsChange={handleVisibleBoundsChange}
                                        setDisassemblyStep={setDisassemblyStep}
                                        setDisassemblyPlaying={setDisassemblyPlaying}
                                        setExplodeAmount={setExplodeAmount}
                                    />
                                </Canvas>
                            </Viewer3DErrorBoundary>
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
