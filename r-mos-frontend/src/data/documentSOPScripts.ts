import {
    ActionType,
    ErrorCategory,
    SOPFailureReason,
    SOPPrecondition,
    SOPScriptAdjudication,
    SOPStepAdjudication,
    SOPValidation,
    SystemState,
} from '@/adjudication';

interface DocumentSOPEntry {
    code: string;
    title: string;
    faultCategory: string;
    mttrMinutes: number;
    focus: string;
}

const DOCUMENT_SOP_ENTRIES: DocumentSOPEntry[] = [
    {
        code: 'RMOS-SOP-001',
        title: '推理节点未启动 / 服务未注册（Inference Node Not Started / Service Unregistered）',
        faultCategory: '启动链路 / 节点可用性',
        mttrMinutes: 22,
        focus: 'inference_node 与核心服务注册状态',
    },
    {
        code: 'RMOS-SOP-002',
        title: '电机未初始化导致执行拒绝（Motors Uninitialized, Execution Rejected）',
        faultCategory: '执行链路 / 电机状态',
        mttrMinutes: 20,
        focus: '电机初始化与执行前置状态',
    },
    {
        code: 'RMOS-SOP-003',
        title: 'CAN 总线未就绪 / 通道映射错误（CAN Bus Not Ready / Channel Mapping Mismatch）',
        faultCategory: '总线通信 / 驱动链路',
        mttrMinutes: 26,
        focus: 'CAN 总线就绪与映射一致性',
    },
    {
        code: 'RMOS-SOP-004',
        title: 'IMU 数据缺失 / 串口离线（IMU Data Missing / Serial Offline）',
        faultCategory: '传感链路 / IMU',
        mttrMinutes: 24,
        focus: 'IMU 数据流与串口在线状态',
    },
    {
        code: 'RMOS-SOP-005',
        title: '/joint_ref_states 缺失或维度错误（/joint_ref_states Missing or Invalid Dimension）',
        faultCategory: '状态反馈链路 / 关节观测',
        mttrMinutes: 23,
        focus: '关节观测 topic 有效性与维度一致性',
    },
    {
        code: 'RMOS-SOP-006',
        title: '/cmd_vel 控制不生效（控制源锁定在 joy）（/cmd_vel Control Ineffective (Locked to Joy)）',
        faultCategory: '控制输入链路 / 模式切换',
        mttrMinutes: 21,
        focus: '控制源切换与 /cmd_vel 生效路径',
    },
    {
        code: 'RMOS-SOP-007',
        title: '推理启动/停止状态机异常（Inference Start/Stop State Machine Fault）',
        faultCategory: '服务状态机 / 推理控制',
        mttrMinutes: 22,
        focus: 'start/stop 服务状态机一致性',
    },
    {
        code: 'RMOS-SOP-008',
        title: '模型文件缺失 / 加载失败（Model File Missing / Load Failed）',
        faultCategory: '模型资产 / 推理引擎',
        mttrMinutes: 25,
        focus: '模型资产路径与加载日志',
    },
    {
        code: 'RMOS-SOP-009',
        title: 'inference.yaml 参数漂移（Inference YAML Parameter Drift）',
        faultCategory: '配置一致性 / 推理参数',
        mttrMinutes: 24,
        focus: '推理参数漂移与基线比对',
    },
    {
        code: 'RMOS-SOP-010',
        title: '实时优先级设置失败（Realtime Priority Setup Failure）',
        faultCategory: '线程调度 / 实时性',
        mttrMinutes: 27,
        focus: '实时优先级配置与线程调度',
    },
    {
        code: 'RMOS-SOP-011',
        title: '/action 发布频率过低 / 循环超时（/action Low Publish Rate / Loop Overrun）',
        faultCategory: '时序性能 / 推理循环',
        mttrMinutes: 26,
        focus: '推理循环时序与 action 发布频率',
    },
    {
        code: 'RMOS-SOP-012',
        title: '关节越界保护触发（Joint Out-of-Limit Protection Triggered）',
        faultCategory: '安全保护 / 关节限位',
        mttrMinutes: 28,
        focus: '关节限位策略与保护触发条件',
    },
    {
        code: 'RMOS-SOP-013',
        title: 'set_zeros 执行失败 / 零位标定异常（set_zeros Failure / Zero Calibration Fault）',
        faultCategory: '标定链路 / 关节零位',
        mttrMinutes: 24,
        focus: '零位标定命令与回写一致性',
    },
    {
        code: 'RMOS-SOP-014',
        title: 'clear_errors 后错误状态仍存在（Errors Persist After clear_errors）',
        faultCategory: '故障清除 / 电机错误恢复',
        mttrMinutes: 25,
        focus: '电机错误清除与状态回读一致性',
    },
    {
        code: 'RMOS-SOP-015',
        title: 'reset_joints 失败或复位不到位（reset_joints Failure or Incomplete Reset）',
        faultCategory: '复位链路 / 关节归位',
        mttrMinutes: 23,
        focus: '关节复位动作与复位后姿态偏差',
    },
    {
        code: 'RMOS-SOP-016',
        title: 'BeyondMimic 模式资源缺失 / 切换失败（BeyondMimic Resource Missing / Switch Failure）',
        faultCategory: '模式切换 / 动作模仿链路',
        mttrMinutes: 27,
        focus: 'BeyondMimic 资源就绪与模式切换',
    },
    {
        code: 'RMOS-SOP-017',
        title: 'Attn-Enc 感知输入缺失（Attn-Enc Perception Input Missing）',
        faultCategory: '感知输入 / 注意力编码链路',
        mttrMinutes: 26,
        focus: '感知输入流与编码前检查点',
    },
    {
        code: 'RMOS-SOP-018',
        title: '推理输出抖动 / 发散（Inference Output Jitter / Divergence）',
        faultCategory: '推理链路 / 输出稳定性',
        mttrMinutes: 28,
        focus: '输出稳定性与抖动阈值',
    },
    {
        code: 'RMOS-SOP-019',
        title: 'DDS 配置未生效 / 发现延迟过高（DDS Profile Not Applied / Discovery Latency High）',
        faultCategory: '中间件通信 / DDS QoS',
        mttrMinutes: 27,
        focus: 'DDS QoS 配置加载与发现时延',
    },
    {
        code: 'RMOS-SOP-020',
        title: 'Sim2Real 策略频率不一致（Sim2Real Policy Frequency Mismatch）',
        faultCategory: '仿真部署一致性 / 频率链路',
        mttrMinutes: 30,
        focus: '策略频率与部署环境一致性',
    },
];

const DEFAULT_FAILURE_REASONS: SOPFailureReason[] = [
    {
        code: 'ERR_DOC_STEP',
        category: ErrorCategory.INCOMPLETE_ACTION,
        description: '文档步骤尚未确认完成',
        severity: 'minor',
        teachingResponse: {
            showHint: true,
            hintContent: '先按步骤完成检查与记录，再推进到下一步。',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 2,
            allowContinue: true,
            recordToReport: true,
        },
    },
];

const BLOCK_ON_FAILURE: SOPStepAdjudication['onFailure'] = {
    action: 'block',
    message: '请完成当前文档步骤后再推进。',
};

function difficultyFromMttr(mttrMinutes: number): SOPScriptAdjudication['difficulty'] {
    if (mttrMinutes <= 22) return 'beginner';
    if (mttrMinutes <= 26) return 'intermediate';
    return 'advanced';
}

function inferTargetModule(entry: DocumentSOPEntry): SOPScriptAdjudication['targetModule'] {
    const source = `${entry.title} ${entry.faultCategory}`.toLowerCase();
    if (source.includes('can') || source.includes('dds') || source.includes('总线')) return 'base';
    if (source.includes('电机') || source.includes('关节') || source.includes('set_zeros') || source.includes('reset_joints')) {
        return 'left_leg';
    }
    if (source.includes('cmd_vel') || source.includes('joy') || source.includes('模式切换')) return 'base';
    return 'torso';
}

function createStep(
    stepId: string,
    stepIndex: number,
    title: string,
    description: string,
    nextStepId: string,
    stateTransition: SystemState | null = null,
): SOPStepAdjudication {
    const preconditions: SOPPrecondition[] = [];
    const validations: SOPValidation[] = [];
    return {
        stepId,
        stepIndex,
        title,
        description,
        action: ActionType.FOCUS_CAMERA,
        targetParts: [],
        requiredTool: null,
        preconditions,
        validations,
        failureReasons: DEFAULT_FAILURE_REASONS,
        onSuccess: {
            nextStepId,
            stateTransition,
        },
        onFailure: BLOCK_ON_FAILURE,
    };
}

function createDocumentSOP(entry: DocumentSOPEntry): SOPScriptAdjudication {
    const scriptId = entry.code.toLowerCase().replace('rmos-sop-', 'sop-rmos-') + '-doc';
    const targetModule = inferTargetModule(entry);

    return {
        sopId: scriptId,
        title: `${entry.code}｜${entry.title}`,
        version: 'v1.0-doc-bridge',
        targetModule,
        estimatedTime: entry.mttrMinutes * 60,
        difficulty: difficultyFromMttr(entry.mttrMinutes),
        steps: [
            createStep(
                'step_001',
                1,
                '故障识别与边界确认',
                `故障分类：${entry.faultCategory}；目标 MTTR：<= ${entry.mttrMinutes} 分钟。先确认当前演练场景、seed、任务编号和基线快照。`,
                'step_002',
            ),
            createStep(
                'step_002',
                2,
                '执行安全前置（S2）',
                '按 S2-1 ~ S2-4b 完成仿真模式确认、推理暂停、快照采集与落库确认，缺证据必须记录 evidence_incomplete。',
                'step_003',
            ),
            createStep(
                'step_003',
                3,
                '执行诊断流程（D）',
                `围绕「${entry.focus}」按 D-01 ~ D-05 排查：先健康检查，再参数一致性、链路稳定性、日志关键词，最后锁定唯一根因。`,
                'step_004',
            ),
            createStep(
                'step_004',
                4,
                '执行修复流程（F）',
                '按 F-R3 -> F-R1 -> F-R2 -> F-R4 -> F-R5 的优先级最小变更修复；每轮只改一个根因并立即复测。',
                'step_005',
            ),
            createStep(
                'step_005',
                5,
                '执行验证回归（V）',
                '完成 V-01 ~ V-03：创建回归任务、等待 120s 采样、核对诊断字段与自动评分（M-03）。',
                'step_006',
            ),
            createStep(
                'step_006',
                6,
                '证据归档与升级判断',
                '整理命令、日志、快照、评分与工单结论；若出现不可恢复风险按升级路径转人工 L2。',
                'end',
                SystemState.VERIFICATION,
            ),
        ],
    };
}

export const DOCUMENT_SOP_SCRIPTS: SOPScriptAdjudication[] = DOCUMENT_SOP_ENTRIES.map(createDocumentSOP);
