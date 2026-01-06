/**
 * Report 相关类型定义
 * 与后端 schemas/report.py 完全对齐 (V2.3)
 */

// 评分细分 - 对齐 ScoreBreakdown
export interface ScoreBreakdown {
    professionalism: number             // 专业性得分（0-25）
    compliance: number                  // 规范性得分（0-25）
    efficiency: number                  // 效率得分（0-25）
    safety: number                      // 安全性得分（0-25）
}

// 步骤得分 - 对齐 StepScore
export interface StepScore {
    step_index: number                  // 步骤索引
    step_title: string                  // 步骤标题
    score: number                       // 得分
    max_score: number                   // 满分
    deductions: Array<{                 // 扣分项
        reason: string
        points: number
        [key: string]: any
    }>
    remarks?: string                    // 备注
}

// 任务报告 - 对齐 TaskReport
export interface TaskReport {
    task_id: number                     // 任务ID
    task_title: string                  // 任务标题
    sop_name?: string                   // SOP名称（可能为NULL）
    user_id?: number                    // 用户ID
    started_at: string                  // 开始时间
    completed_at: string                // 完成时间
    total_duration_seconds: number      // 总用时（秒）
    expected_duration_seconds?: number  // 预期用时（秒）
    final_score: number                 // 最终得分
    pass_score: number                  // 及格分数
    is_passed: boolean                  // 是否通过
    score_breakdown: ScoreBreakdown     // 评分细分
    step_scores: StepScore[]            // 各步骤得分
    total_steps: number                 // 总步骤数
    completed_steps: number             // 已完成步骤数
    skipped_steps: number               // 跳过步骤数
    error_count: number                 // 错误次数
    recommendations: string[]           // 改进建议
    generated_at: string                // 报告生成时间
}

// 报告摘要（用于列表展示）
export interface TaskReportSummary {
    task_id: number
    task_title: string
    completed_at: string
    final_score: number
    is_passed: boolean
    total_duration_seconds: number
}
