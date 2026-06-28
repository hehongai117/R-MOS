/**
 * SOPMaintenancePanels.tsx - SOP 维保页面纯展示面板
 *
 * 从 SOPMaintenancePage.tsx 下沉的渲染片段（零件详情面板、左栏隔离子组件、
 * 左栏 SOP 列表）。纯展示，所有数据与回调由页面经 props 注入。
 */
import { Button, Card, Descriptions, Empty, Space, Tag, Typography } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import type { PartInfo } from '@/components/Viewer3D/manifestPartMetadata';
import PartInspector from '@/components/Viewer3D/PartInspector';
import { getLinkDisplayName, linkHasDetailParts } from '@/components/Viewer3D/assemblyTree';
import type { DetailPart } from '@/components/Viewer3D/partsManifest';
import { getDetailPartDetailRecord } from '@/data/maintenanceKnowledge';
import type { useSOPSceneSync } from '@/adjudication/ui/useSOPSceneSync';
import type { ViewState } from './sopMaintenanceConfig';
import { SOP_EXECUTION_STATE_LABEL, SOP_EXECUTION_STATE_TAG_COLOR } from './sopMaintenanceConfig';

const { Title, Text } = Typography;

type DetailRecord = NonNullable<ReturnType<typeof getDetailPartDetailRecord>>;
type IsolationSets = { targetLinks: readonly string[]; fadeLinks: readonly string[]; referenceLinks: readonly string[] };

interface PartDetailPanelProps {
    activeDetailRecord: DetailRecord | null;
    selectedPart: PartInfo | null;
    groupNames: Record<string, string>;
    getGroupParts: (group: string) => PartInfo[];
    partInspectorLink: string | null;
    selectedScrewId: string | null;
    isolationLevel: number;
    l2TargetLink: string | null;
    l2DetailParts: DetailPart[];
    l2SelectedPartIdx: number | null;
    onSubPartSelect: (linkName: string, partIndex: number, part: DetailPart) => void;
    onSelectPart: (part: PartInfo | null) => void;
}

export function PartDetailPanel({
    activeDetailRecord,
    selectedPart,
    groupNames,
    getGroupParts,
    partInspectorLink,
    selectedScrewId,
    isolationLevel,
    l2TargetLink,
    l2DetailParts,
    l2SelectedPartIdx,
    onSubPartSelect,
    onSelectPart,
}: PartDetailPanelProps) {
    return (
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
                                onClick={() => onSelectPart(null)}
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
                    title={`${groupNames[selectedPart.group]} 零件列表`}
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
                                onClick={() => onSelectPart(part)}
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
                                    onClick={() => onSubPartSelect(l2TargetLink, idx, part)}
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
}

interface LeftRailIsolationControlsProps {
    viewState: ViewState;
    isolationSets: IsolationSets | null;
    l2TargetLink: string | null;
    partMetadata: Record<string, PartInfo>;
    onPartSelect: (part: PartInfo) => void;
    onEnterL2: (linkName: string) => void;
}

export function LeftRailIsolationControls({
    viewState,
    isolationSets,
    l2TargetLink,
    partMetadata,
    onPartSelect,
    onEnterL2,
}: LeftRailIsolationControlsProps) {
    if (viewState !== 'ISOLATED' || !isolationSets) return null;
    return (
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
                                const part = partMetadata[linkName];
                                if (part) {
                                    onPartSelect(part);
                                    return;
                                }
                                if (linkHasDetailParts(linkName)) {
                                    onEnterL2(linkName);
                                }
                            }}
                        >
                            {getLinkDisplayName(linkName)}
                        </Button>
                    );
                })}
            </Space>
        </Card>
    );
}

interface LeftRailSopListProps {
    isSopListExpanded: boolean;
    onToggleExpanded: () => void;
    availableSopScripts: Array<{ sopId: string; title: string }>;
    linkedSOPId: string | null;
    onSelectSop: (sopId: string) => void;
    sopSceneSync: ReturnType<typeof useSOPSceneSync>;
}

export function LeftRailSopList({
    isSopListExpanded,
    onToggleExpanded,
    availableSopScripts,
    linkedSOPId,
    onSelectSop,
    sopSceneSync,
}: LeftRailSopListProps) {
    return (
        <Card
            size="small"
            title="📚 SOP 列表"
            extra={(
                <Button
                    size="small"
                    type="text"
                    onClick={onToggleExpanded}
                >
                    {isSopListExpanded ? '收起 SOP 列表' : '展开 SOP 列表'}
                </Button>
            )}
        >
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Text type="secondary" style={{ fontSize: 12 }}>
                    默认收起，避免打断执行；展开后可切换到其他 SOP。
                </Text>
                {isSopListExpanded ? (
                    availableSopScripts.length > 0 ? availableSopScripts.map((sop) => {
                        const isActive = sop.sopId === linkedSOPId;
                        return (
                            <Button
                                key={`sop-link-${sop.sopId}`}
                                size="small"
                                type={isActive ? 'primary' : 'default'}
                                block
                                onClick={() => onSelectSop(sop.sopId)}
                            >
                                {sop.title}
                            </Button>
                        );
                    }) : (
                        <Text type="secondary" style={{ fontSize: 12, textAlign: 'center', display: 'block' }}>
                            暂无可用 SOP，请先选择机器人或联系教师配置。
                        </Text>
                    )
                ) : null}
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
}
