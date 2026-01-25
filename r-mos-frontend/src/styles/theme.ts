/**
 * R-MOS 工业控制台主题配置（V2.3 新增 - Phase 3）
 * 
 * 设计理念：
 * - 高对比度深色主题，减少视觉疲劳
 * - 运维态色板：冷色系背景 + 高饱和度警告
 * - 工业质感：金属灰、深蓝、霓虹绿
 */
import type { ThemeConfig } from 'antd';

// ===== 色板定义 =====

// 主色调 - 科技蓝
const PRIMARY_COLOR = '#1890ff';
const PRIMARY_HOVER = '#40a9ff';
const PRIMARY_ACTIVE = '#096dd9';

// 背景色 - 深空灰
const BG_BASE = '#0d1117';           // 最深背景（页面）
const BG_CONTAINER = '#161b22';       // 容器背景（卡片）
const BG_ELEVATED = '#21262d';        // 悬浮背景（弹窗）
const BG_SPOTLIGHT = '#30363d';       // 高亮背景（选中）

// 边框色
const BORDER_BASE = '#30363d';
const BORDER_STRONG = '#484f58';

// 文字色 - 高对比度
const TEXT_PRIMARY = '#e6edf3';       // 主要文字
const TEXT_SECONDARY = '#8b949e';     // 次要文字
const TEXT_TERTIARY = '#6e7681';      // 辅助文字
const TEXT_DISABLED = '#484f58';      // 禁用文字

// 状态色 - 高饱和度警告
const SUCCESS = '#3fb950';            // 成功/在线
const WARNING = '#d29922';            // 警告
const ERROR = '#f85149';              // 错误/危险
const INFO = '#58a6ff';               // 信息

// 特殊色 - 工业仪表风格
const NEON_GREEN = '#00ff9f';         // 霓虹绿（在线状态）
const NEON_BLUE = '#00d4ff';          // 霓虹蓝（数据流）
const ALARM_RED = '#ff3333';          // 报警红（故障）
const CAUTION_AMBER = '#ffcc00';      // 警戒黄（临界）

// ===== AntD 主题配置 =====

export const darkTheme: ThemeConfig = {
    // 组件级 token
    token: {
        // 品牌色
        colorPrimary: PRIMARY_COLOR,
        colorLink: PRIMARY_COLOR,
        colorLinkHover: PRIMARY_HOVER,
        colorLinkActive: PRIMARY_ACTIVE,

        // 成功/警告/错误/信息
        colorSuccess: SUCCESS,
        colorWarning: WARNING,
        colorError: ERROR,
        colorInfo: INFO,

        // 背景色
        colorBgContainer: BG_CONTAINER,
        colorBgElevated: BG_ELEVATED,
        colorBgLayout: BG_BASE,
        colorBgSpotlight: BG_SPOTLIGHT,

        // 文字色
        colorText: TEXT_PRIMARY,
        colorTextSecondary: TEXT_SECONDARY,
        colorTextTertiary: TEXT_TERTIARY,
        colorTextDisabled: TEXT_DISABLED,

        // 边框
        colorBorder: BORDER_BASE,
        colorBorderSecondary: BORDER_STRONG,

        // 圆角 - 工业风偏硬朗
        borderRadius: 4,
        borderRadiusLG: 6,
        borderRadiusSM: 2,

        // 阴影 - 深色主题弱化阴影
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.45)',
        boxShadowSecondary: '0 4px 12px rgba(0, 0, 0, 0.5)',
    },

    // 组件覆盖
    components: {
        // 布局
        Layout: {
            headerBg: BG_CONTAINER,
            siderBg: BG_CONTAINER,
            bodyBg: BG_BASE,
            triggerBg: BG_ELEVATED,
            triggerColor: TEXT_PRIMARY,
        },

        // 菜单
        Menu: {
            darkItemBg: 'transparent',
            darkSubMenuItemBg: BG_ELEVATED,
            darkItemSelectedBg: 'rgba(24, 144, 255, 0.15)',
            darkItemHoverBg: 'rgba(255, 255, 255, 0.08)',
            darkItemColor: TEXT_SECONDARY,
            darkItemSelectedColor: PRIMARY_COLOR,
        },

        // 卡片
        Card: {
            colorBgContainer: BG_CONTAINER,
            colorBorderSecondary: BORDER_BASE,
        },

        // 表格
        Table: {
            colorBgContainer: BG_CONTAINER,
            headerBg: BG_ELEVATED,
            headerColor: TEXT_PRIMARY,
            rowHoverBg: 'rgba(255, 255, 255, 0.04)',
            borderColor: BORDER_BASE,
        },

        // 标签
        Tag: {
            defaultBg: BG_ELEVATED,
            defaultColor: TEXT_PRIMARY,
        },

        // 按钮
        Button: {
            defaultBg: BG_ELEVATED,
            defaultBorderColor: BORDER_BASE,
            defaultColor: TEXT_PRIMARY,
        },

        // 输入框
        Input: {
            colorBgContainer: BG_ELEVATED,
            colorBorder: BORDER_BASE,
            hoverBorderColor: PRIMARY_COLOR,
            activeBorderColor: PRIMARY_COLOR,
        },

        // 选择器
        Select: {
            colorBgContainer: BG_ELEVATED,
            colorBgElevated: BG_ELEVATED,
            optionSelectedBg: 'rgba(24, 144, 255, 0.15)',
        },

        // 统计数值
        Statistic: {
            colorTextDescription: TEXT_SECONDARY,
        },

        // 警告框
        Alert: {
            colorInfoBg: 'rgba(88, 166, 255, 0.1)',
            colorInfoBorder: INFO,
            colorSuccessBg: 'rgba(63, 185, 80, 0.1)',
            colorSuccessBorder: SUCCESS,
            colorWarningBg: 'rgba(210, 153, 34, 0.1)',
            colorWarningBorder: WARNING,
            colorErrorBg: 'rgba(248, 81, 73, 0.1)',
            colorErrorBorder: ERROR,
        },

        // 进度条
        Progress: {
            defaultColor: PRIMARY_COLOR,
        },
    },

    // 启用暗色算法
    algorithm: undefined, // 使用自定义 token，不用内置 algorithm
};

// ===== 工业状态色导出（供组件使用）=====

export const industrialColors = {
    // 系统状态
    online: NEON_GREEN,
    offline: TEXT_DISABLED,
    connecting: WARNING,

    // 故障等级
    normal: SUCCESS,
    warning: CAUTION_AMBER,
    critical: ALARM_RED,

    // 数据流
    dataFlow: NEON_BLUE,
    stale: WARNING,

    // 背景
    bg: {
        base: BG_BASE,
        container: BG_CONTAINER,
        elevated: BG_ELEVATED,
        spotlight: BG_SPOTLIGHT,
    },

    // 文字
    text: {
        primary: TEXT_PRIMARY,
        secondary: TEXT_SECONDARY,
        tertiary: TEXT_TERTIARY,
    },
};

export default darkTheme;
