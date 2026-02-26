import {
    ActionType,
    ErrorCategory,
    PreconditionType,
    SOPFailureReason,
    SOPPrecondition,
    SOPScriptAdjudication,
    SOPStepAdjudication,
    SOPValidation,
    SystemState,
    ValidationType,
} from '@/adjudication';

type Difficulty = SOPScriptAdjudication['difficulty'];
type TargetModule = SOPScriptAdjudication['targetModule'];

type StepDraft = {
    title: string;
    description: string;
    action: ActionType;
    targetParts?: string[];
    requiredTool?: string | null;
    preconditions?: SOPPrecondition[];
    validations?: SOPValidation[];
    finalStateTransition?: SystemState | null;
};

const DEFAULT_FAILURE_REASONS: SOPFailureReason[] = [
    {
        code: 'ERR_WRONG_ORDER',
        category: ErrorCategory.WRONG_ORDER,
        description: '操作顺序错误',
        severity: 'major',
        teachingResponse: {
            showHint: true,
            hintContent: '请严格按照 SOP 顺序执行当前步骤。',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 5,
            allowContinue: false,
            recordToReport: true,
        },
    },
    {
        code: 'ERR_WRONG_TOOL',
        category: ErrorCategory.WRONG_TOOL,
        description: '工具选择错误',
        severity: 'major',
        teachingResponse: {
            showHint: true,
            hintContent: '请选择步骤要求的工具后重试。',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 4,
            allowContinue: false,
            recordToReport: true,
        },
    },
    {
        code: 'ERR_INCOMPLETE',
        category: ErrorCategory.INCOMPLETE_ACTION,
        description: '步骤动作未完成',
        severity: 'major',
        teachingResponse: {
            showHint: true,
            hintContent: '请完成当前步骤的全部交互后再推进。',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 3,
            allowContinue: false,
            recordToReport: true,
        },
    },
];

const BLOCK_ON_FAILURE: SOPStepAdjudication['onFailure'] = {
    action: 'block',
    message: '裁决未通过，请按提示完成当前步骤。',
};

const TORSO_M3_SET = [
    'screw_torso_m3x10_001',
    'screw_torso_m3x10_002',
    'screw_torso_m3x10_003',
    'screw_torso_m3x10_004',
    'screw_torso_m3x10_005',
    'screw_torso_m3x10_006',
    'screw_torso_m3x10_007',
    'screw_torso_m3x10_008',
];

const TORSO_M4_SET = [
    'screw_torso_m4x12_001',
    'screw_torso_m4x12_002',
    'screw_torso_m4x12_003',
    'screw_torso_m4x12_004',
    'screw_torso_m4x12_005',
    'screw_torso_m4x12_006',
];

const LEFT_FOOT_M4_SET = [
    'screw_left_foot_m4x10_001',
    'screw_left_foot_m4x10_002',
    'screw_left_foot_m4x10_003',
    'screw_left_foot_m4x10_004',
];

const RIGHT_FOOT_M4_SET = [
    'screw_right_foot_m4x10_001',
    'screw_right_foot_m4x10_002',
    'screw_right_foot_m4x10_003',
    'screw_right_foot_m4x10_004',
];

const LEFT_ANKLE_M4_SET = [
    'screw_left_ankle_m4x8_001',
    'screw_left_ankle_m4x8_002',
    'screw_left_ankle_m4x8_003',
    'screw_left_ankle_m4x8_004',
];

const RIGHT_ANKLE_M4_SET = [
    'screw_right_ankle_m4x8_001',
    'screw_right_ankle_m4x8_002',
    'screw_right_ankle_m4x8_003',
    'screw_right_ankle_m4x8_004',
];

const TORSO_CHEST_COVER = 'frame_torso_chest';

const resolveFootCoverPartId = (ankleRoll: string): string => {
    if (ankleRoll === 'left_ankle_roll_link') {
        return 'left_foot_rubber';
    }
    if (ankleRoll === 'right_ankle_roll_link') {
        return 'right_foot_rubber';
    }
    return ankleRoll;
};

const makeToolPrecondition = (toolId: string, message: string): SOPPrecondition => ({
    type: PreconditionType.TOOL_EQUIPPED,
    params: { toolId },
    errorMessage: message,
});

const makeToolValidation = (toolId: string): SOPValidation => ({
    type: ValidationType.TOOL_MATCHED,
    params: { toolId },
    isRequired: true,
});

const makeAllScrewsValidation = (screwIds: string[]): SOPValidation => ({
    type: ValidationType.ALL_SCREWS_EXTRACTED,
    params: { screwIds },
    isRequired: true,
});

const focusStep = (title: string, description: string, target: string): StepDraft => ({
    title,
    description,
    action: ActionType.FOCUS_CAMERA,
    targetParts: [target],
    requiredTool: null,
});

const toolStep = (title: string, description: string, toolId: string): StepDraft => ({
    title,
    description,
    action: ActionType.SELECT_TOOL,
    targetParts: [],
    requiredTool: toolId,
    validations: [makeToolValidation(toolId)],
});

const screwStep = (title: string, description: string, screwIds: string[], toolId: string): StepDraft => ({
    title,
    description,
    action: ActionType.ROTATE_SCREW,
    targetParts: screwIds,
    requiredTool: toolId,
    preconditions: [makeToolPrecondition(toolId, `请先选择 ${toolId} 工具`)],
    validations: [makeAllScrewsValidation(screwIds)],
});

const detachStep = (title: string, description: string, target: string): StepDraft => ({
    title,
    description,
    action: ActionType.DETACH_PART,
    targetParts: [target],
    requiredTool: null,
});

const removeStep = (title: string, description: string, target: string): StepDraft => ({
    title,
    description,
    action: ActionType.REMOVE_PART,
    targetParts: [target],
    requiredTool: null,
});

const unplugStep = (title: string, description: string, target: string): StepDraft => ({
    title,
    description,
    action: ActionType.UNPLUG_CONNECTOR,
    targetParts: [target],
    requiredTool: null,
});

function toSteps(stepDrafts: StepDraft[]): SOPStepAdjudication[] {
    return stepDrafts.map((draft, idx) => {
        const isLast = idx === stepDrafts.length - 1;
        const stepId = `step_${String(idx + 1).padStart(3, '0')}`;
        const nextStepId = isLast ? 'end' : `step_${String(idx + 2).padStart(3, '0')}`;
        return {
            stepId,
            stepIndex: idx + 1,
            title: draft.title,
            description: draft.description,
            action: draft.action,
            targetParts: draft.targetParts ?? [],
            requiredTool: draft.requiredTool ?? null,
            preconditions: draft.preconditions ?? [],
            validations: draft.validations ?? [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: {
                nextStepId,
                stateTransition: isLast ? (draft.finalStateTransition ?? SystemState.VERIFICATION) : null,
            },
            onFailure: BLOCK_ON_FAILURE,
        };
    });
}

function createSOP(
    sopId: string,
    title: string,
    targetModule: TargetModule,
    difficulty: Difficulty,
    estimatedTimeMinutes: number,
    stepDrafts: StepDraft[],
): SOPScriptAdjudication {
    return {
        sopId,
        title,
        version: '2.0.0-hw',
        targetModule,
        estimatedTime: estimatedTimeMinutes * 60,
        difficulty,
        steps: toSteps(stepDrafts),
    };
}

function buildL8(core: string, points: string[]): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并完成维保隔离。', core),
        focusStep('定位检查点 1', '检查第一处关键结构/连接区域。', points[0]),
        focusStep('定位检查点 2', '检查第二处关键结构/连接区域。', points[1]),
        focusStep('定位检查点 3', '检查第三处关键结构/连接区域。', points[2]),
        focusStep('定位检查点 4', '检查第四处关键结构/连接区域。', points[3]),
        focusStep('定位检查点 5', '检查第五处关键结构/连接区域。', points[4]),
        focusStep('定位检查点 6', '检查第六处关键结构/连接区域。', points[5]),
        focusStep('结束确认', '确认本轮点检无遗漏并准备提交。', core),
    ];
}

function buildL9(core: string, joints: string[]): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并完成维保隔离。', core),
        focusStep('起点关节定位', '定位链路起点关节。', joints[0]),
        focusStep('次级关节定位', '定位链路次级关节。', joints[1]),
        focusStep('中段关节定位', '定位链路中段关节。', joints[2]),
        focusStep('末端关节定位', '定位链路末端关节。', joints[3]),
        focusStep('末端执行段定位', '定位末端执行关节。', joints[4]),
        focusStep('中段回查', '回查中段关节状态一致性。', joints[2]),
        focusStep('起点回查', '回查起点关节状态一致性。', joints[0]),
        focusStep('结束确认', '完成点检记录并结束。', core),
    ];
}

function buildL10(core: string, joints: string[], cover: string): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并完成维保隔离。', core),
        focusStep('髋关节定位', '定位髋关节并检查姿态。', joints[0]),
        focusStep('大腿滚转定位', '定位大腿滚转并检查连接。', joints[1]),
        focusStep('大腿俯仰定位', '定位大腿俯仰并检查连接。', joints[2]),
        focusStep('膝关节定位', '定位膝关节并检查配合。', joints[3]),
        focusStep('踝俯仰定位', '定位踝俯仰并检查配合。', joints[4]),
        focusStep('踝横滚定位', '定位踝横滚并检查配合。', joints[5]),
        focusStep('覆盖件定位', '检查覆盖件贴合情况。', cover),
        focusStep('膝关节回查', '回查膝关节链路稳定性。', joints[3]),
        focusStep('结束确认', '完成下肢链路点检。', core),
    ];
}

function buildM16Torso(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('定位躯干作业区', '定位躯干总成作业区域。', 'torso_link'),
        toolStep('选择 2.5mm 工具', '准备拆卸躯干夹板螺丝。', 'hex_2.5'),
        screwStep('拆卸 M3×10 螺丝组', '拆卸躯干夹板 8 颗螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除胸腔夹板', '打开躯干覆盖作业区。', TORSO_CHEST_COVER),
        focusStep('检查电机区域', '检查躯干电机周边是否异常。', 'torso_link'),
        focusStep('检查主控板区域', '检查主控板区域连接与固定。', 'torso_link'),
        unplugStep('检查线束连接', '检查躯干线束连接状态。', 'torso_link'),
        focusStep('回装区域定位', '定位回装基准位。', 'torso_link'),
        focusStep('覆盖区对齐', '确认覆盖区对齐关系。', 'torso_link'),
        focusStep('紧固顺序复核', '确认紧固顺序按对角执行。', 'torso_link'),
        focusStep('外观复核 1', '复核外观与间隙。', 'torso_link'),
        focusStep('外观复核 2', '复核关键连接位。', 'torso_link'),
        focusStep('内部区域复核', '复核内部件干涉风险。', 'torso_link'),
        focusStep('结构复核', '复核结构稳定性。', 'torso_link'),
        focusStep('结束确认', '完成躯干开盖检查。', 'torso_link'),
    ];
}

function buildM18Foot(
    ankleRoll: string,
    anklePitch: string,
    knee: string,
    thighPitch: string,
    screwSet: string[],
): StepDraft[] {
    const coverPartId = resolveFootCoverPartId(ankleRoll);
    return [
        focusStep('安全确认', '确认设备断电并固定。', ankleRoll),
        focusStep('定位脚底覆盖区', '定位脚底覆盖件作业区域。', ankleRoll),
        removeStep('移除脚底软胶覆盖件', '拆除脚底软胶覆盖件。', coverPartId),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('拆卸脚底 M4×10 螺丝组', '拆卸脚底 4 颗螺丝。', screwSet, 'hex_3'),
        detachStep('分离脚底板', '分离脚底板并检查配合面。', ankleRoll),
        focusStep('检查踝俯仰', '检查踝俯仰连接状态。', anklePitch),
        focusStep('检查膝关节', '检查膝关节连接状态。', knee),
        focusStep('脚底板回装定位', '定位脚底板回装基准。', ankleRoll),
        focusStep('覆盖件回装定位', '定位覆盖件回装基准。', ankleRoll),
        focusStep('链路复核 1', '复核大腿到踝部链路。', thighPitch),
        focusStep('链路复核 2', '复核踝关节链路。', anklePitch),
        focusStep('链路复核 3', '复核脚底板链路。', ankleRoll),
        focusStep('贴合复核', '复核覆盖件贴合状态。', ankleRoll),
        focusStep('膝关节回查', '回查膝关节稳定性。', knee),
        focusStep('大腿回查', '回查大腿连接稳定性。', thighPitch),
        focusStep('底座回查', '回查底座支撑稳定性。', 'base_link'),
        focusStep('结束确认', '完成脚底覆盖件拆装检查。', ankleRoll),
    ];
}

function buildM20Ankle(
    ankleRoll: string,
    anklePitch: string,
    knee: string,
    thighPitch: string,
    footScrewSet: string[],
    ankleScrewSet: string[],
): StepDraft[] {
    const coverPartId = resolveFootCoverPartId(ankleRoll);
    return [
        focusStep('安全确认', '确认设备断电并固定。', ankleRoll),
        focusStep('定位脚底覆盖区', '定位脚底覆盖件作业区域。', ankleRoll),
        removeStep('移除脚底软胶覆盖件', '拆除脚底软胶覆盖件。', coverPartId),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('拆卸脚底 M4×10 螺丝组', '拆卸脚底 4 颗螺丝。', footScrewSet, 'hex_3'),
        detachStep('分离脚底板', '分离脚底板。', ankleRoll),
        focusStep('踝俯仰可达性检查', '确认踝俯仰可达并无遮挡。', anklePitch),
        screwStep('拆卸踝关节 M4×8 螺丝组', '拆卸踝关节 4 颗螺丝。', ankleScrewSet, 'hex_3'),
        detachStep('分离踝俯仰件', '分离踝俯仰件。', anklePitch),
        focusStep('检查膝关节连接', '检查膝关节连接状态。', knee),
        focusStep('检查大腿俯仰连接', '检查大腿俯仰连接状态。', thighPitch),
        focusStep('踝俯仰回装定位', '定位踝俯仰回装基准。', anklePitch),
        focusStep('脚底板回装定位', '定位脚底板回装基准。', ankleRoll),
        focusStep('覆盖件回装定位', '定位覆盖件回装基准。', ankleRoll),
        focusStep('脚踝同轴复核', '复核脚踝同轴状态。', anklePitch),
        focusStep('脚底平面复核', '复核脚底平面状态。', ankleRoll),
        focusStep('膝踝链路复核', '复核膝踝链路。', knee),
        focusStep('大腿链路复核', '复核大腿链路。', thighPitch),
        focusStep('底座姿态复核', '复核底座姿态稳定性。', 'base_link'),
        focusStep('结束确认', '完成踝总成拆检。', ankleRoll),
    ];
}

function buildH24Torso(primary: 'motor' | 'pcb'): StepDraft[] {
    const primaryLabel = primary === 'motor' ? '电机' : '主控板';
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('主模块定位', '定位躯干主模块。', 'torso_link'),
        focusStep('支撑模块定位', '定位底座支撑模块。', 'base_link'),
        toolStep('选择 3mm 工具', '准备拆卸躯干主固定螺丝。', 'hex_3'),
        screwStep('拆卸 M4×12 螺丝组', '拆卸躯干主固定 6 颗螺丝。', TORSO_M4_SET, 'hex_3'),
        focusStep('分离作业区确认', '确认躯干外层作业区可达。', 'torso_link'),
        toolStep('切换 2.5mm 工具', '准备拆卸夹板螺丝。', 'hex_2.5'),
        screwStep('拆卸 M3×10 螺丝组', '拆卸夹板 8 颗螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除躯干覆盖层', '移除躯干覆盖层。', TORSO_CHEST_COVER),
        focusStep('内部件检查 1', `检查${primaryLabel}区域。`, 'torso_link'),
        focusStep('内部件检查 2', '检查次级关键件区域。', 'torso_link'),
        focusStep('主链路检查', '检查主链路是否顺畅。', 'torso_link'),
        focusStep('支撑链路检查', '检查支撑链路是否稳定。', 'base_link'),
        unplugStep('连接器检查', '检查并复核连接器状态。', 'torso_link'),
        focusStep('内部件复核 1', `复核${primaryLabel}区域状态。`, 'torso_link'),
        focusStep('内部件复核 2', '复核次级关键件状态。', 'torso_link'),
        focusStep('覆盖层回装定位', '定位覆盖层回装基准。', 'torso_link'),
        focusStep('外层回装定位', '定位外层回装基准。', 'torso_link'),
        focusStep('主链路复核', '复核主链路。', 'torso_link'),
        focusStep('支撑链路复核', '复核支撑链路。', 'base_link'),
        focusStep('底座姿态复核', '复核底座姿态稳定性。', 'base_link'),
        focusStep('躯干姿态复核', '复核躯干姿态稳定性。', 'torso_link'),
        focusStep('关键点终检', `终检${primaryLabel}作业区域。`, 'torso_link'),
        focusStep('结束确认', `完成躯干${primaryLabel}维保流程。`, 'torso_link'),
    ];
}

function buildH22Ankle(
    ankleRoll: string,
    anklePitch: string,
    knee: string,
    thighPitch: string,
    footScrewSet: string[],
    ankleScrewSet: string[],
): StepDraft[] {
    const coverPartId = resolveFootCoverPartId(ankleRoll);
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('定位脚底模块', '定位脚底模块。', ankleRoll),
        focusStep('定位踝关节模块', '定位踝关节模块。', anklePitch),
        removeStep('移除脚底软胶覆盖件', '拆除脚底软胶覆盖件。', coverPartId),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('拆卸脚底 M4×10 螺丝组', '拆卸脚底螺丝组。', footScrewSet, 'hex_3'),
        detachStep('分离脚底板组件', '分离脚底板组件。', ankleRoll),
        focusStep('第二组件定位', '定位踝俯仰组件。', anklePitch),
        toolStep('保持 3mm 工具', '继续拆卸踝关节螺丝。', 'hex_3'),
        screwStep('拆卸踝关节 M4×8 螺丝组', '拆卸踝关节螺丝组。', ankleScrewSet, 'hex_3'),
        focusStep('覆盖区域暴露确认', '确认覆盖区域已暴露内部。', ankleRoll),
        focusStep('内部件检查 1', '检查膝关节连接区。', knee),
        focusStep('内部件检查 2', '检查大腿连接区。', thighPitch),
        unplugStep('连接状态检查', '检查连接状态与线束走向。', anklePitch),
        focusStep('目标件回装定位', '定位踝俯仰回装基准。', anklePitch),
        focusStep('覆盖区回装定位', '定位覆盖区回装基准。', ankleRoll),
        focusStep('脚底组件回装定位', '定位脚底组件回装基准。', ankleRoll),
        focusStep('链路复核 1', '复核踝关节链路。', anklePitch),
        focusStep('链路复核 2', '复核脚底模块链路。', ankleRoll),
        focusStep('结构复核', '复核底座到腿部结构链路。', 'base_link'),
        focusStep('关键件复核 1', '复核膝关节关键点。', knee),
        focusStep('关键件复核 2', '复核大腿关键点。', thighPitch),
        focusStep('结束确认', '完成踝总成大修流程。', 'torso_link'),
    ];
}

function buildH30Annual(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('躯干定位', '定位躯干模块。', 'torso_link'),
        focusStep('左臂起点定位', '定位左肩 Pitch。', 'left_arm_pitch_link'),
        focusStep('左臂中段定位', '定位左肩 Roll。', 'left_arm_roll_link'),
        focusStep('左臂末端定位', '定位左前臂。', 'left_elbow_yaw_link'),
        focusStep('左腿髋关节定位', '定位左髋关节。', 'left_thigh_yaw_link'),
        focusStep('左腿膝关节定位', '定位左膝关节。', 'left_knee_link'),
        focusStep('左腿踝关节定位', '定位左踝关节。', 'left_ankle_pitch_link'),
        focusStep('右腿髋关节定位', '定位右髋关节。', 'right_thigh_yaw_link'),
        focusStep('右腿膝关节定位', '定位右膝关节。', 'right_knee_link'),
        focusStep('右腿踝关节定位', '定位右踝关节。', 'right_ankle_pitch_link'),
        focusStep('左脚覆盖区检查', '检查左脚覆盖区。', 'left_ankle_roll_link'),
        focusStep('右脚覆盖区检查', '检查右脚覆盖区。', 'right_ankle_roll_link'),
        removeStep('移除左脚软胶覆盖件', '拆除左脚底软胶覆盖件。', 'left_foot_rubber'),
        removeStep('移除右脚软胶覆盖件', '拆除右脚底软胶覆盖件。', 'right_foot_rubber'),
        toolStep('选择 3mm 工具', '准备拆卸下肢螺丝。', 'hex_3'),
        screwStep('拆卸左脚底螺丝组', '拆卸左脚底 M4×10 螺丝组。', LEFT_FOOT_M4_SET, 'hex_3'),
        screwStep('拆卸右脚底螺丝组', '拆卸右脚底 M4×10 螺丝组。', RIGHT_FOOT_M4_SET, 'hex_3'),
        screwStep('拆卸左踝螺丝组', '拆卸左踝 M4×8 螺丝组。', LEFT_ANKLE_M4_SET, 'hex_3'),
        screwStep('拆卸右踝螺丝组', '拆卸右踝 M4×8 螺丝组。', RIGHT_ANKLE_M4_SET, 'hex_3'),
        toolStep('切换 2.5mm 工具', '准备拆卸躯干夹板螺丝。', 'hex_2.5'),
        screwStep('拆卸躯干夹板螺丝组', '拆卸躯干 M3×10 螺丝组。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除躯干覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('躯干电机区检查', '检查躯干电机区域。', 'torso_link'),
        focusStep('主控板区检查', '检查主控板区域。', 'torso_link'),
        unplugStep('躯干线束检查', '检查躯干线束连接。', 'torso_link'),
        focusStep('覆盖区回装定位', '定位躯干覆盖区回装基准。', 'torso_link'),
        focusStep('左腿链路复核', '复核左腿链路。', 'left_ankle_roll_link'),
        focusStep('右腿链路复核', '复核右腿链路。', 'right_ankle_roll_link'),
        focusStep('左臂链路复核', '复核左臂链路。', 'left_elbow_pitch_link'),
        focusStep('躯干姿态复核', '复核躯干姿态。', 'torso_link'),
        focusStep('结束确认', '完成年度大保养流程。', 'base_link'),
    ];
}

function buildH21Structural(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('躯干主区定位', '定位躯干主区。', 'torso_link'),
        toolStep('选择 3mm 工具', '准备拆卸主固定螺丝。', 'hex_3'),
        screwStep('拆卸躯干 M4×12 螺丝组', '拆卸躯干主固定螺丝。', TORSO_M4_SET, 'hex_3'),
        focusStep('左脚区域定位', '定位左脚底区域。', 'left_ankle_roll_link'),
        removeStep('移除左脚软胶覆盖件', '拆除左脚底软胶覆盖件。', 'left_foot_rubber'),
        screwStep('拆卸左脚底 M4×10 螺丝组', '拆卸左脚底螺丝。', LEFT_FOOT_M4_SET, 'hex_3'),
        focusStep('右脚区域定位', '定位右脚底区域。', 'right_ankle_roll_link'),
        removeStep('移除右脚软胶覆盖件', '拆除右脚底软胶覆盖件。', 'right_foot_rubber'),
        screwStep('拆卸右脚底 M4×10 螺丝组', '拆卸右脚底螺丝。', RIGHT_FOOT_M4_SET, 'hex_3'),
        toolStep('切换 2.5mm 工具', '准备拆卸夹板螺丝。', 'hex_2.5'),
        screwStep('拆卸躯干 M3×10 螺丝组', '拆卸躯干夹板螺丝。', TORSO_M3_SET, 'hex_2.5'),
        focusStep('预紧力复核 1', '复核躯干连接位。', 'torso_link'),
        focusStep('预紧力复核 2', '复核左脚连接位。', 'left_ankle_roll_link'),
        focusStep('预紧力复核 3', '复核右脚连接位。', 'right_ankle_roll_link'),
        focusStep('链路复核 1', '复核左腿链路。', 'left_ankle_pitch_link'),
        focusStep('链路复核 2', '复核右腿链路。', 'right_ankle_pitch_link'),
        focusStep('链路复核 3', '复核底座链路。', 'base_link'),
        focusStep('结构复核 1', '复核躯干结构。', 'torso_link'),
        focusStep('结构复核 2', '复核左腿结构。', 'left_knee_link'),
        focusStep('结构复核 3', '复核右腿结构。', 'right_knee_link'),
        focusStep('最终复核', '复核整体预紧一致性。', 'torso_link'),
        focusStep('结束确认', '完成结构预紧力重检。', 'base_link'),
    ];
}

function buildH22ChestAudit(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('躯干定位', '定位躯干作业区。', 'torso_link'),
        toolStep('选择 2.5mm 工具', '准备拆卸夹板螺丝。', 'hex_2.5'),
        screwStep('第一轮拆卸 M3×10 螺丝组', '执行第一轮夹板螺丝拆卸。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('第一轮移除覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('第一轮电机区检查', '检查电机区状态。', 'torso_link'),
        focusStep('第一轮主控板区检查', '检查主控板区状态。', 'torso_link'),
        focusStep('第一轮回装定位', '定位第一轮回装基准。', 'torso_link'),
        toolStep('再次确认 2.5mm 工具', '准备执行第二轮拆装。', 'hex_2.5'),
        focusStep('第二轮拆卸路径复核', '复核第二轮夹板拆卸路径。', 'torso_link'),
        focusStep('第二轮覆盖区状态确认', '确认第二轮覆盖区状态。', 'torso_link'),
        focusStep('第二轮电机区检查', '复检电机区状态。', 'torso_link'),
        focusStep('第二轮主控板区检查', '复检主控板区状态。', 'torso_link'),
        unplugStep('线束状态核查', '核查线束连接稳定性。', 'torso_link'),
        focusStep('第二轮回装定位', '定位第二轮回装基准。', 'torso_link'),
        focusStep('结构复核 1', '复核夹板区域结构。', 'torso_link'),
        focusStep('结构复核 2', '复核躯干主结构。', 'torso_link'),
        focusStep('链路复核 1', '复核躯干到底座链路。', 'base_link'),
        focusStep('链路复核 2', '复核躯干内部链路。', 'torso_link'),
        focusStep('审计记录核对', '核对重复拆装记录完整性。', 'torso_link'),
        focusStep('结束确认', '完成胸腔夹板拆装审计。', 'torso_link'),
    ];
}

function buildH22FootAudit(
    ankleRoll: string,
    anklePitch: string,
    knee: string,
    footScrewSet: string[],
): StepDraft[] {
    const coverPartId = resolveFootCoverPartId(ankleRoll);
    return [
        focusStep('安全确认', '确认设备断电并固定。', ankleRoll),
        focusStep('脚底区域定位', '定位脚底区域。', ankleRoll),
        removeStep('移除覆盖件', '移除脚底软胶覆盖件。', coverPartId),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('第一轮拆卸脚底 M4×10 螺丝组', '执行第一轮脚底螺丝拆卸。', footScrewSet, 'hex_3'),
        detachStep('第一轮分离脚底板', '分离脚底板。', ankleRoll),
        focusStep('第一轮踝关节检查', '检查踝关节状态。', anklePitch),
        focusStep('第一轮膝关节检查', '检查膝关节状态。', knee),
        focusStep('第一轮回装定位', '定位第一轮回装基准。', ankleRoll),
        toolStep('保持 3mm 工具', '准备执行第二轮拆装。', 'hex_3'),
        focusStep('第二轮拆卸路径复核', '复核第二轮脚底螺丝拆卸路径。', ankleRoll),
        focusStep('第二轮分离路径复核', '复核第二轮脚底板分离路径。', ankleRoll),
        focusStep('第二轮踝关节检查', '复检踝关节状态。', anklePitch),
        focusStep('第二轮膝关节检查', '复检膝关节状态。', knee),
        focusStep('第二轮回装定位', '定位第二轮回装基准。', ankleRoll),
        focusStep('结构复核 1', '复核脚底板结构。', ankleRoll),
        focusStep('结构复核 2', '复核踝关节结构。', anklePitch),
        focusStep('链路复核 1', '复核膝踝链路。', knee),
        focusStep('链路复核 2', '复核底座支撑链路。', 'base_link'),
        focusStep('审计记录核对', '核对重复拆装记录完整性。', ankleRoll),
        focusStep('最终复核', '复核脚底区域稳定性。', ankleRoll),
        focusStep('结束确认', '完成脚底板拆装审计。', ankleRoll),
    ];
}

function buildH24Baseline(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('主模块定位', '定位底座主模块。', 'base_link'),
        focusStep('支撑模块定位', '定位躯干支撑模块。', 'torso_link'),
        removeStep('移除左脚软胶覆盖件', '拆除左脚底软胶覆盖件。', 'left_foot_rubber'),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('拆卸左脚底 M4×10 螺丝组', '拆卸左脚底螺丝。', LEFT_FOOT_M4_SET, 'hex_3'),
        detachStep('分离左脚底组件', '分离左脚底组件。', 'left_ankle_roll_link'),
        toolStep('切换 2.5mm 工具', '准备拆卸躯干螺丝。', 'hex_2.5'),
        screwStep('拆卸躯干 M3×10 螺丝组', '拆卸躯干夹板螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除躯干覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('内部件检查 1', '检查躯干关键区域。', 'torso_link'),
        focusStep('内部件检查 2', '检查左臂关键区域。', 'left_arm_pitch_link'),
        focusStep('主链路检查', '检查底座主链路。', 'base_link'),
        focusStep('支撑链路检查', '检查躯干支撑链路。', 'torso_link'),
        unplugStep('连接器检查', '检查躯干连接状态。', 'torso_link'),
        focusStep('内部件复核 1', '复核躯干关键区域。', 'torso_link'),
        focusStep('内部件复核 2', '复核左臂关键区域。', 'left_arm_pitch_link'),
        focusStep('覆盖区回装定位', '定位躯干覆盖区回装基准。', 'torso_link'),
        focusStep('组件回装定位', '定位左脚底组件回装基准。', 'left_ankle_roll_link'),
        focusStep('主链路复核', '复核底座主链路。', 'base_link'),
        focusStep('支撑链路复核', '复核躯干支撑链路。', 'torso_link'),
        focusStep('底座姿态复核', '复核底座姿态。', 'base_link'),
        focusStep('躯干姿态复核', '复核躯干姿态。', 'torso_link'),
        focusStep('关键点终检', '终检关键点状态。', 'torso_link'),
        focusStep('结束确认', '完成全身关键点基线复核。', 'torso_link'),
    ];
}

function buildH28MasterFlow(): StepDraft[] {
    return [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('躯干主区定位', '定位躯干主区。', 'torso_link'),
        toolStep('选择 2.5mm 工具', '准备拆卸躯干螺丝。', 'hex_2.5'),
        screwStep('拆卸躯干 M3×10 螺丝组', '拆卸躯干夹板螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除躯干覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('躯干内部检查 1', '检查电机区域。', 'torso_link'),
        focusStep('躯干内部检查 2', '检查主控板区域。', 'torso_link'),
        unplugStep('躯干连接检查', '检查躯干连接状态。', 'torso_link'),
        focusStep('躯干回装定位', '定位躯干回装基准。', 'torso_link'),
        focusStep('左踝模块定位', '定位左踝模块。', 'left_ankle_roll_link'),
        removeStep('移除左脚软胶覆盖件', '拆除左脚底软胶覆盖件。', 'left_foot_rubber'),
        toolStep('切换 3mm 工具', '准备拆卸左脚底螺丝。', 'hex_3'),
        screwStep('拆卸左脚底 M4×10 螺丝组', '拆卸左脚底螺丝。', LEFT_FOOT_M4_SET, 'hex_3'),
        detachStep('分离左脚底组件', '分离左脚底组件。', 'left_ankle_roll_link'),
        screwStep('拆卸左踝 M4×8 螺丝组', '拆卸左踝螺丝。', LEFT_ANKLE_M4_SET, 'hex_3'),
        detachStep('分离左踝俯仰件', '分离左踝俯仰件。', 'left_ankle_pitch_link'),
        focusStep('左踝链路复核', '复核左踝链路。', 'left_knee_link'),
        focusStep('右踝模块定位', '定位右踝模块。', 'right_ankle_roll_link'),
        removeStep('移除右脚软胶覆盖件', '拆除右脚底软胶覆盖件。', 'right_foot_rubber'),
        screwStep('拆卸右脚底 M4×10 螺丝组', '拆卸右脚底螺丝。', RIGHT_FOOT_M4_SET, 'hex_3'),
        detachStep('分离右脚底组件', '分离右脚底组件。', 'right_ankle_roll_link'),
        screwStep('拆卸右踝 M4×8 螺丝组', '拆卸右踝螺丝。', RIGHT_ANKLE_M4_SET, 'hex_3'),
        detachStep('分离右踝俯仰件', '分离右踝俯仰件。', 'right_ankle_pitch_link'),
        focusStep('右踝链路复核', '复核右踝链路。', 'right_knee_link'),
        focusStep('左右链路一致性复核', '复核左右链路一致性。', 'base_link'),
        focusStep('左臂链路复核', '复核左臂链路。', 'left_elbow_pitch_link'),
        focusStep('躯干姿态复核', '复核躯干姿态。', 'torso_link'),
        focusStep('全身姿态复核', '复核全身姿态。', 'base_link'),
        focusStep('记录与审计复核', '复核维保记录完整性。', 'torso_link'),
        focusStep('结束确认', '完成主维保综合流程。', 'base_link'),
    ];
}

const HARDWARE_SOP_SCRIPTS: SOPScriptAdjudication[] = [
    // 低难度 5 条
    createSOP('sop-hw-l01', '躯干外观与连接点检', 'torso', 'beginner', 12, buildL8('torso_link', [
        'torso_link',
        'left_arm_pitch_link',
        'right_arm_pitch_link',
        'base_link',
        'left_thigh_yaw_link',
        'right_thigh_yaw_link',
    ])),
    createSOP('sop-hw-l02', '左臂关节快速点检', 'left_arm', 'beginner', 14, buildL9('torso_link', [
        'left_arm_pitch_link',
        'left_arm_roll_link',
        'left_arm_yaw_link',
        'left_elbow_pitch_link',
        'left_elbow_yaw_link',
    ])),
    createSOP('sop-hw-l03', '左腿链路快速点检', 'left_leg', 'beginner', 16, buildL10('base_link', [
        'left_thigh_yaw_link',
        'left_thigh_roll_link',
        'left_thigh_pitch_link',
        'left_knee_link',
        'left_ankle_pitch_link',
        'left_ankle_roll_link',
    ], 'left_ankle_roll_link')),
    createSOP('sop-hw-l04', '右腿链路快速点检', 'right_leg', 'beginner', 16, buildL10('base_link', [
        'right_thigh_yaw_link',
        'right_thigh_roll_link',
        'right_thigh_pitch_link',
        'right_knee_link',
        'right_ankle_pitch_link',
        'right_ankle_roll_link',
    ], 'right_ankle_roll_link')),
    createSOP('sop-hw-l05', '双脚底覆盖件点检', 'base', 'beginner', 12, buildL8('base_link', [
        'left_ankle_roll_link',
        'right_ankle_roll_link',
        'left_ankle_pitch_link',
        'right_ankle_pitch_link',
        'left_knee_link',
        'right_knee_link',
    ])),

    // 中难度 10 条
    createSOP('sop-hw-m01', '躯干开盖检查', 'torso', 'intermediate', 24, buildM16Torso()),
    createSOP('sop-hw-m02', '躯干电机可达性检查', 'torso', 'intermediate', 28, [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('定位躯干主区', '定位躯干主区。', 'torso_link'),
        toolStep('选择 3mm 工具', '准备拆卸主固定螺丝。', 'hex_3'),
        screwStep('拆卸 M4×12 螺丝组', '拆卸躯干主固定螺丝。', TORSO_M4_SET, 'hex_3'),
        focusStep('分离作业区确认', '确认躯干外层作业区可达。', 'torso_link'),
        toolStep('切换 2.5mm 工具', '准备拆卸夹板螺丝。', 'hex_2.5'),
        screwStep('拆卸 M3×10 螺丝组', '拆卸夹板螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('电机可达性检查 1', '检查电机区域可达性。', 'torso_link'),
        focusStep('电机可达性检查 2', '复核电机区域可达性。', 'torso_link'),
        unplugStep('线束可达性检查', '检查线束通道可达性。', 'torso_link'),
        focusStep('回装定位 1', '定位覆盖区回装基准。', 'torso_link'),
        focusStep('回装定位 2', '定位外层回装基准。', 'torso_link'),
        focusStep('链路复核 1', '复核躯干主链路。', 'torso_link'),
        focusStep('链路复核 2', '复核底座支撑链路。', 'base_link'),
        focusStep('姿态复核', '复核躯干姿态。', 'torso_link'),
        focusStep('关键点终检', '终检电机作业区。', 'torso_link'),
        focusStep('结束确认', '完成躯干电机可达性检查。', 'torso_link'),
    ]),
    createSOP('sop-hw-m03', '躯干主控板可达性检查', 'torso', 'intermediate', 26, [
        ...buildM16Torso().slice(0, 8),
        focusStep('主控板可达性检查 1', '检查主控板区域可达性。', 'torso_link'),
        focusStep('主控板可达性检查 2', '复核主控板区域可达性。', 'torso_link'),
        focusStep('回装定位 1', '定位回装基准。', 'torso_link'),
        focusStep('回装定位 2', '复核回装对齐。', 'torso_link'),
        focusStep('链路复核 1', '复核躯干链路。', 'torso_link'),
        focusStep('链路复核 2', '复核底座链路。', 'base_link'),
        focusStep('姿态复核', '复核躯干姿态。', 'torso_link'),
        focusStep('结束确认', '完成躯干主控板可达性检查。', 'torso_link'),
    ]),
    createSOP('sop-hw-m04', '躯干主固定螺丝复检', 'torso', 'intermediate', 22, [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('定位躯干主区', '定位躯干主区。', 'torso_link'),
        toolStep('选择 3mm 工具', '准备拆卸主固定螺丝。', 'hex_3'),
        screwStep('拆卸 M4×12 螺丝组', '拆卸主固定螺丝。', TORSO_M4_SET, 'hex_3'),
        focusStep('螺孔检查 1', '检查第一组螺孔状态。', 'torso_link'),
        focusStep('螺孔检查 2', '检查第二组螺孔状态。', 'torso_link'),
        focusStep('接口检查', '检查主接口区域状态。', 'torso_link'),
        focusStep('结构检查', '检查结构连接状态。', 'torso_link'),
        focusStep('回装定位 1', '定位回装基准。', 'torso_link'),
        focusStep('回装定位 2', '复核回装对齐。', 'torso_link'),
        focusStep('预紧复核 1', '复核预紧顺序。', 'torso_link'),
        focusStep('预紧复核 2', '复核预紧一致性。', 'torso_link'),
        focusStep('链路复核 1', '复核躯干链路。', 'torso_link'),
        focusStep('链路复核 2', '复核底座链路。', 'base_link'),
        focusStep('结束确认', '完成躯干主固定螺丝复检。', 'torso_link'),
    ]),
    createSOP('sop-hw-m05', '左脚底软胶拆装检查', 'left_leg', 'intermediate', 26,
        buildM18Foot('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET),
    ),
    createSOP('sop-hw-m06', '右脚底软胶拆装检查', 'right_leg', 'intermediate', 26,
        buildM18Foot('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', 'right_thigh_pitch_link', RIGHT_FOOT_M4_SET),
    ),
    createSOP('sop-hw-m07', '左踝总成拆检', 'left_leg', 'intermediate', 30,
        buildM20Ankle('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET),
    ),
    createSOP('sop-hw-m08', '右踝总成拆检', 'right_leg', 'intermediate', 30,
        buildM20Ankle('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', 'right_thigh_pitch_link', RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET),
    ),
    createSOP('sop-hw-m09', '双脚紧固一致性维保', 'base', 'intermediate', 28, [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('定位左脚模块', '定位左脚模块。', 'left_ankle_roll_link'),
        focusStep('定位右脚模块', '定位右脚模块。', 'right_ankle_roll_link'),
        removeStep('移除左脚软胶覆盖件', '拆除左脚底软胶覆盖件。', 'left_foot_rubber'),
        removeStep('移除右脚软胶覆盖件', '拆除右脚底软胶覆盖件。', 'right_foot_rubber'),
        toolStep('选择 3mm 工具', '准备拆卸脚底螺丝。', 'hex_3'),
        screwStep('拆卸左脚底螺丝组', '拆卸左脚底 M4×10 螺丝组。', LEFT_FOOT_M4_SET, 'hex_3'),
        screwStep('拆卸右脚底螺丝组', '拆卸右脚底 M4×10 螺丝组。', RIGHT_FOOT_M4_SET, 'hex_3'),
        screwStep('拆卸左踝螺丝组', '拆卸左踝 M4×8 螺丝组。', LEFT_ANKLE_M4_SET, 'hex_3'),
        screwStep('拆卸右踝螺丝组', '拆卸右踝 M4×8 螺丝组。', RIGHT_ANKLE_M4_SET, 'hex_3'),
        focusStep('左脚链路复核 1', '复核左脚底板链路。', 'left_ankle_roll_link'),
        focusStep('右脚链路复核 1', '复核右脚底板链路。', 'right_ankle_roll_link'),
        focusStep('左脚链路复核 2', '复核左踝链路。', 'left_ankle_pitch_link'),
        focusStep('右脚链路复核 2', '复核右踝链路。', 'right_ankle_pitch_link'),
        focusStep('左腿链路复核', '复核左腿下肢链路。', 'left_knee_link'),
        focusStep('右腿链路复核', '复核右腿下肢链路。', 'right_knee_link'),
        focusStep('一致性复核 1', '复核左右脚底一致性。', 'base_link'),
        focusStep('一致性复核 2', '复核左右踝一致性。', 'base_link'),
        focusStep('结束确认', '完成双脚紧固一致性维保。', 'base_link'),
    ]),
    createSOP('sop-hw-m10', '躯干-底座连接维保', 'torso', 'intermediate', 22, [
        focusStep('安全确认', '确认设备断电并固定。', 'base_link'),
        focusStep('定位躯干连接区', '定位躯干连接区。', 'torso_link'),
        focusStep('定位底座支撑区', '定位底座支撑区。', 'base_link'),
        toolStep('选择 3mm 工具', '准备拆卸躯干主固定螺丝。', 'hex_3'),
        screwStep('拆卸 M4×12 螺丝组', '拆卸躯干主固定螺丝。', TORSO_M4_SET, 'hex_3'),
        focusStep('分离作业区确认', '确认躯干作业区可达。', 'torso_link'),
        focusStep('连接面检查 1', '检查躯干连接面。', 'torso_link'),
        focusStep('连接面检查 2', '检查底座连接面。', 'base_link'),
        focusStep('紧固位检查', '检查紧固位状态。', 'torso_link'),
        focusStep('回装定位 1', '定位躯干回装基准。', 'torso_link'),
        focusStep('回装定位 2', '定位底座回装基准。', 'base_link'),
        focusStep('链路复核 1', '复核躯干链路。', 'torso_link'),
        focusStep('链路复核 2', '复核底座链路。', 'base_link'),
        focusStep('姿态复核', '复核躯干与底座姿态。', 'base_link'),
        focusStep('结束确认', '完成躯干-底座连接维保。', 'base_link'),
    ]),

    // 高难度 15 条
    createSOP('sop-hw-h01', '躯干电机更换全流程', 'torso', 'advanced', 45, buildH24Torso('motor')),
    createSOP('sop-hw-h02', '躯干主控板更换全流程', 'torso', 'advanced', 45, buildH24Torso('pcb')),
    createSOP('sop-hw-h03', '左踝总成大修', 'left_leg', 'advanced', 42,
        buildH22Ankle('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET),
    ),
    createSOP('sop-hw-h04', '右踝总成大修', 'right_leg', 'advanced', 42,
        buildH22Ankle('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', 'right_thigh_pitch_link', RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET),
    ),
    createSOP('sop-hw-h05', '双踝总成同步维保', 'base', 'advanced', 50, [
        ...buildM20Ankle('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET).slice(0, 13),
        ...buildM20Ankle('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', 'right_thigh_pitch_link', RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET).slice(0, 13),
    ]),
    createSOP('sop-hw-h06', '躯干+左踝跨模块维保', 'torso', 'advanced', 46, [
        ...buildH22Ankle('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET).slice(0, 10),
        ...buildM16Torso().slice(0, 8),
        focusStep('跨模块链路复核 1', '复核躯干到左腿链路。', 'torso_link'),
        focusStep('跨模块链路复核 2', '复核左踝到膝链路。', 'left_knee_link'),
        focusStep('跨模块链路复核 3', '复核底座支撑链路。', 'base_link'),
        focusStep('结束确认', '完成躯干+左踝跨模块维保。', 'torso_link'),
    ]),
    createSOP('sop-hw-h07', '躯干+右踝跨模块维保', 'torso', 'advanced', 46, [
        ...buildH22Ankle('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', 'right_thigh_pitch_link', RIGHT_FOOT_M4_SET, RIGHT_ANKLE_M4_SET).slice(0, 10),
        ...buildM16Torso().slice(0, 8),
        focusStep('跨模块链路复核 1', '复核躯干到右腿链路。', 'torso_link'),
        focusStep('跨模块链路复核 2', '复核右踝到膝链路。', 'right_knee_link'),
        focusStep('跨模块链路复核 3', '复核底座支撑链路。', 'base_link'),
        focusStep('结束确认', '完成躯干+右踝跨模块维保。', 'torso_link'),
    ]),
    createSOP('sop-hw-h08', '下肢年度大保养', 'base', 'advanced', 60, buildH30Annual()),
    createSOP('sop-hw-h09', '左侧链路深度维保', 'left_leg', 'advanced', 48, [
        ...buildL9('torso_link', ['left_arm_pitch_link', 'left_arm_roll_link', 'left_arm_yaw_link', 'left_elbow_pitch_link', 'left_elbow_yaw_link']).slice(0, 6),
        ...buildM20Ankle('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', 'left_thigh_pitch_link', LEFT_FOOT_M4_SET, LEFT_ANKLE_M4_SET).slice(0, 10),
        focusStep('左侧链路复核 1', '复核左臂链路。', 'left_elbow_yaw_link'),
        focusStep('左侧链路复核 2', '复核左腿链路。', 'left_knee_link'),
        focusStep('左侧链路复核 3', '复核左踝链路。', 'left_ankle_roll_link'),
        focusStep('左侧链路复核 4', '复核左髋链路。', 'left_thigh_yaw_link'),
        focusStep('左侧链路复核 5', '复核躯干连接链路。', 'torso_link'),
        focusStep('结束确认', '完成左侧链路深度维保。', 'torso_link'),
    ]),
    createSOP('sop-hw-h10', '右侧链路深度维保', 'right_leg', 'advanced', 48, [
        focusStep('安全确认', '确认设备断电并固定。', 'torso_link'),
        focusStep('右腿髋定位', '定位右髋关节。', 'right_thigh_yaw_link'),
        focusStep('右腿膝定位', '定位右膝关节。', 'right_knee_link'),
        focusStep('右踝定位', '定位右踝关节。', 'right_ankle_pitch_link'),
        removeStep('移除右脚软胶覆盖件', '拆除右脚底软胶覆盖件。', 'right_foot_rubber'),
        toolStep('选择 3mm 工具', '准备拆卸右脚底螺丝。', 'hex_3'),
        screwStep('拆卸右脚底 M4×10 螺丝组', '拆卸右脚底螺丝组。', RIGHT_FOOT_M4_SET, 'hex_3'),
        detachStep('分离右脚底板', '分离右脚底板。', 'right_ankle_roll_link'),
        screwStep('拆卸右踝 M4×8 螺丝组', '拆卸右踝螺丝组。', RIGHT_ANKLE_M4_SET, 'hex_3'),
        detachStep('分离右踝俯仰件', '分离右踝俯仰件。', 'right_ankle_pitch_link'),
        focusStep('躯干主区定位', '定位躯干主区。', 'torso_link'),
        toolStep('切换 2.5mm 工具', '准备拆卸躯干螺丝。', 'hex_2.5'),
        screwStep('拆卸躯干 M3×10 螺丝组', '拆卸躯干夹板螺丝。', TORSO_M3_SET, 'hex_2.5'),
        removeStep('移除躯干覆盖区', '移除躯干覆盖区。', TORSO_CHEST_COVER),
        focusStep('右侧链路复核 1', '复核右髋链路。', 'right_thigh_yaw_link'),
        focusStep('右侧链路复核 2', '复核右膝链路。', 'right_knee_link'),
        focusStep('右侧链路复核 3', '复核右踝链路。', 'right_ankle_roll_link'),
        focusStep('右侧链路复核 4', '复核躯干链路。', 'torso_link'),
        focusStep('右侧链路复核 5', '复核底座链路。', 'base_link'),
        focusStep('结构终检', '终检右侧链路结构稳定性。', 'torso_link'),
        focusStep('结束确认', '完成右侧链路深度维保。', 'torso_link'),
        focusStep('复核补充 1', '补充复核右腿踝区。', 'right_ankle_pitch_link'),
        focusStep('复核补充 2', '补充复核躯干区。', 'torso_link'),
        focusStep('最终确认', '完成最终确认。', 'base_link'),
    ]),
    createSOP('sop-hw-h11', '结构预紧力重检', 'base', 'advanced', 44, buildH21Structural()),
    createSOP('sop-hw-h12', '胸腔夹板反复拆装审计', 'torso', 'advanced', 44, buildH22ChestAudit()),
    createSOP('sop-hw-h13', '双脚底板反复拆装审计', 'base', 'advanced', 44, [
        ...buildH22FootAudit('left_ankle_roll_link', 'left_ankle_pitch_link', 'left_knee_link', LEFT_FOOT_M4_SET).slice(0, 11),
        ...buildH22FootAudit('right_ankle_roll_link', 'right_ankle_pitch_link', 'right_knee_link', RIGHT_FOOT_M4_SET).slice(0, 11),
    ]),
    createSOP('sop-hw-h14', '全身关键点基线复核', 'base', 'advanced', 46, buildH24Baseline()),
    createSOP('sop-hw-h15', '主维保流程（综合版）', 'base', 'advanced', 55, buildH28MasterFlow()),
];

const assertNoEmptySteps = (scripts: SOPScriptAdjudication[]): void => {
    scripts.forEach((sop) => {
        sop.steps.forEach((step) => {
            if (
                step.action !== ActionType.SELECT_TOOL &&
                step.action !== ActionType.ROTATE_SCREW &&
                step.targetParts.length === 0
            ) {
                throw new Error(`硬件 SOP 存在空目标步骤: ${sop.sopId}#${step.stepId}`);
            }
            if (
                step.action === ActionType.ROTATE_SCREW &&
                step.validations.length === 0
            ) {
                throw new Error(`硬件 SOP 缺少螺丝验证: ${sop.sopId}#${step.stepId}`);
            }
        });
    });
};

assertNoEmptySteps(HARDWARE_SOP_SCRIPTS);

export { HARDWARE_SOP_SCRIPTS };
