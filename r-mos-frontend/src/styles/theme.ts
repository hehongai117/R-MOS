import type { ThemeConfig } from 'antd'

const PRIMARY = '#2D7DD2'
const PRIMARY_HOVER = '#3d8de2'
const PRIMARY_ACTIVE = '#2365ab'

const BG_BASE = '#0a0a0f'
const BG_SURFACE = '#13131a'
const BG_ELEVATED = '#1c1c27'
const BG_OVERLAY = '#252535'

const BORDER_DEFAULT = 'rgba(255,255,255,0.10)'
const BORDER_STRONG = 'rgba(255,255,255,0.18)'

const TEXT_PRIMARY = '#e8edf4'
const TEXT_SECONDARY = '#8b95a5'
const TEXT_MUTED = '#4a5568'

const SUCCESS = '#2EC4B6'
const WARNING = '#F4A261'
const ERROR = '#E63946'

export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: PRIMARY,
    colorLink: PRIMARY,
    colorLinkHover: PRIMARY_HOVER,
    colorLinkActive: PRIMARY_ACTIVE,
    colorSuccess: SUCCESS,
    colorWarning: WARNING,
    colorError: ERROR,
    colorInfo: PRIMARY,
    colorBgLayout: BG_BASE,
    colorBgBase: BG_BASE,
    colorBgContainer: BG_ELEVATED,
    colorBgElevated: BG_OVERLAY,
    colorText: TEXT_PRIMARY,
    colorTextSecondary: TEXT_SECONDARY,
    colorTextTertiary: TEXT_MUTED,
    colorTextDisabled: TEXT_MUTED,
    colorBorder: BORDER_DEFAULT,
    colorBorderSecondary: BORDER_STRONG,
    borderRadius: 8,
    borderRadiusSM: 4,
    borderRadiusLG: 12,
    boxShadow: '0 14px 28px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(45, 125, 210, 0.08)',
    boxShadowSecondary:
      '0 20px 42px rgba(0, 0, 0, 0.26), 0 0 0 1px rgba(45, 125, 210, 0.12)',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  components: {
    Layout: {
      bodyBg: BG_BASE,
      headerBg: BG_SURFACE,
      siderBg: BG_SURFACE,
      triggerBg: BG_OVERLAY,
      triggerColor: TEXT_PRIMARY,
    },
    Card: {
      colorBgContainer: BG_SURFACE,
      colorBorderSecondary: BORDER_DEFAULT,
    },
    Button: {
      defaultBg: BG_ELEVATED,
      defaultBorderColor: BORDER_DEFAULT,
      defaultColor: TEXT_PRIMARY,
      primaryShadow: 'none',
    },
    Input: {
      colorBgContainer: BG_ELEVATED,
      colorBorder: BORDER_DEFAULT,
      hoverBorderColor: PRIMARY,
      activeBorderColor: PRIMARY,
      colorTextPlaceholder: TEXT_MUTED,
    },
    Table: {
      colorBgContainer: BG_SURFACE,
      headerBg: BG_ELEVATED,
      headerColor: TEXT_PRIMARY,
      borderColor: BORDER_DEFAULT,
      rowHoverBg: 'rgba(255,255,255,0.03)',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: BG_ELEVATED,
      darkItemSelectedBg: 'rgba(45,125,210,0.15)',
      darkItemHoverBg: 'rgba(255,255,255,0.05)',
      darkItemColor: TEXT_SECONDARY,
      darkItemSelectedColor: PRIMARY,
    },
  },
}

export const industrialColors = {
  online: SUCCESS,
  offline: TEXT_MUTED,
  connecting: WARNING,
  normal: SUCCESS,
  warning: WARNING,
  critical: ERROR,
  dataFlow: PRIMARY,
  stale: WARNING,
  bg: {
    base: BG_BASE,
    surface: BG_SURFACE,
    elevated: BG_ELEVATED,
    overlay: BG_OVERLAY,
  },
  text: {
    primary: TEXT_PRIMARY,
    secondary: TEXT_SECONDARY,
    muted: TEXT_MUTED,
  },
}

export default darkTheme
