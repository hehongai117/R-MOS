/**
 * SOPViewerScene.tsx - SOP 维保 3D 视图 Canvas 场景
 *
 * 从 SOPMaintenancePage.tsx 下沉的 <Canvas> 内部场景：灯光、网格、相机聚焦、
 * 三分支模型查看器（runtime / manifest / atom01）、拆卸动画、OrbitControls。
 * 纯展示，所有数据与回调由页面经 props 注入。
 */
import { Suspense, type ComponentProps, type Dispatch, type SetStateAction } from 'react';
import { OrbitControls } from '@react-three/drei';
import { message } from 'antd';
import type { PartInfo } from '@/components/Viewer3D/manifestPartMetadata';
import { Atom01Interactive } from '@/components/Viewer3D/Atom01Interactive';
import { InteractiveManifestViewer } from '@/components/Viewer3D/InteractiveManifestViewer';
import { CameraController } from '@/components/Viewer3D/CameraController';
import DisassemblyDemoAdjudicated from '@/components/Viewer3D/DisassemblyDemoAdjudicated';
import { DisassemblyAnimation } from '@/components/Viewer3D/DisassemblyAnimation';
import { DetailParts } from '@/components/Viewer3D/DetailParts';
import { RuntimeAssetPreview } from '@/components/Viewer3D/RuntimeAssetPreview';
import type { DetailPart } from '@/components/Viewer3D/partsManifest';
import type { CameraPreset } from '@/components/Viewer3D/assemblyTree';
import type { RuntimeManifestAdapter } from '@/components/Viewer3D/runtimeManifest';
import type { VisibleBounds } from '@/components/Viewer3D/viewerBounds';
import type { ViewState } from './sopMaintenanceConfig';

// 加载指示器
const LoadingFallback = () => (
    <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
);

type ManifestProp = ComponentProps<typeof InteractiveManifestViewer>['manifest'];

interface SOPViewerSceneProps {
    cameraPreset: CameraPreset;
    focusTarget: string | null;
    runtimeManifest: RuntimeManifestAdapter | null;
    runtimePreviewAssetUrl: string | null;
    runtimePreviewAssetPath: string | null;
    manifest: ManifestProp | null;
    currentRobot: { id: number } | null;
    robotId: string | null;
    viewerModelScale: number;
    effectiveExplodeAmount: number;
    visibleLinks: string[];
    clickableLinks: string[];
    fadedLinks: string[];
    referenceLinks: string[];
    subPartEnabledLinks: string[];
    isFullscreen: boolean;
    hoveredPart: PartInfo | null;
    selectedPart: PartInfo | null;
    showDetailParts: boolean;
    viewState: ViewState;
    viewMode: 'normal' | 'explode';
    isolationLevel: number;
    l2TargetLink: string | null;
    l2SelectedPartIdx: number | null;
    selectedOverviewNode: string | null;
    adjudicatedDisassemblyReady: boolean;
    selectedScrewId: string | null;
    selectedToolId: string | null;
    disassemblyPlaying: boolean;
    onPartHover: (part: PartInfo | null) => void;
    onPartSelect: (part: PartInfo | null) => void;
    onPartDoubleClick: (part: PartInfo) => void;
    onSubPartSelect: (linkName: string, partIndex: number, part: DetailPart) => void;
    onSubPartHover: (linkName: string, partIndex: number | null) => void;
    onVisibleBoundsChange: (bounds: VisibleBounds) => void;
    setDisassemblyStep: Dispatch<SetStateAction<string>>;
    setDisassemblyPlaying: Dispatch<SetStateAction<boolean>>;
    setExplodeAmount: Dispatch<SetStateAction<number>>;
}

export function SOPViewerScene({
    cameraPreset,
    focusTarget,
    runtimeManifest,
    runtimePreviewAssetUrl,
    runtimePreviewAssetPath,
    manifest,
    currentRobot,
    robotId,
    viewerModelScale,
    effectiveExplodeAmount,
    visibleLinks,
    clickableLinks,
    fadedLinks,
    referenceLinks,
    subPartEnabledLinks,
    isFullscreen,
    hoveredPart,
    selectedPart,
    showDetailParts,
    viewState,
    viewMode,
    isolationLevel,
    l2TargetLink,
    l2SelectedPartIdx,
    selectedOverviewNode,
    adjudicatedDisassemblyReady,
    selectedScrewId,
    selectedToolId,
    disassemblyPlaying,
    onPartHover,
    onPartSelect,
    onPartDoubleClick,
    onSubPartSelect,
    onSubPartHover,
    onVisibleBoundsChange,
    setDisassemblyStep,
    setDisassemblyPlaying,
    setExplodeAmount,
}: SOPViewerSceneProps) {
    return (
        <>
            <ambientLight intensity={0.5} />
            <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
            <directionalLight position={[-5, 3, -5]} intensity={0.4} />

            <color attach="background" args={['#0a1929']} />

            <gridHelper args={[3, 30, '#1e3a5f', '#1e3a5f']} position={[0, -0.8, 0]} />

            {/* 摄像机聚焦控制器 */}
            <CameraController focusTarget={focusTarget} />

            <Suspense fallback={<LoadingFallback />}>
                {runtimeManifest ? (
                    <RuntimeAssetPreview
                        assetUrl={runtimePreviewAssetUrl}
                        assetPath={runtimePreviewAssetPath}
                        onVisibleBoundsChange={onVisibleBoundsChange}
                    />
                ) : manifest && currentRobot ? (
                    <>
                        <InteractiveManifestViewer
                            manifest={manifest}
                            robotId={currentRobot.id}
                            explodeDistance={effectiveExplodeAmount}
                            visiblePartNames={visibleLinks}
                            clickablePartNames={clickableLinks}
                            fadedPartNames={fadedLinks}
                            fadeOpacity={isFullscreen ? 0.12 : 0.15}
                            onPartHover={onPartHover}
                            onPartSelect={onPartSelect}
                            onPartDoubleClick={onPartDoubleClick}
                            hoveredPart={hoveredPart?.name}
                            selectedPart={selectedPart?.name}
                            highlightLinks={[]}
                        />
                        <DetailParts
                            selectedLink={selectedPart?.name ?? null}
                            visible={showDetailParts}
                        />
                    </>
                ) : robotId ? (
                    <>
                        <Atom01Interactive
                            robotId={robotId}
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
                            onPartHover={onPartHover}
                            onPartSelect={onPartSelect}
                            onPartDoubleClick={onPartDoubleClick}
                            hoveredPart={hoveredPart?.name}
                            selectedPart={selectedPart?.name}
                            isolationLevel={isolationLevel}
                            l2TargetLink={l2TargetLink}
                            l2SelectedPartIdx={l2SelectedPartIdx}
                            onSubPartSelect={onSubPartSelect}
                            onSubPartHover={onSubPartHover}
                            subPartEnabledNames={subPartEnabledLinks}
                            fullscreenMode={isFullscreen}
                            onVisibleBoundsChange={onVisibleBoundsChange}
                        />
                        <DetailParts
                            selectedLink={selectedPart?.name ?? null}
                            visible={showDetailParts}
                        />
                    </>
                ) : null}
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
        </>
    );
}
