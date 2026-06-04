import axios from 'axios'
import { create } from 'zustand'

import { API_ROOT } from '@/api/config'
import type { GuidanceMode } from '@/types/user'

export type UserRole = 'student' | 'teacher' | 'admin'

export interface AuthUser {
  user_id?: number
  email?: string
  full_name?: string
  role: UserRole
  guidance_mode?: GuidanceMode
  welcome_summary?: string | null
  unfinished_session?: Record<string, unknown> | null
  onboarding_completed?: boolean
}

interface Credentials {
  email: string
  password: string
}

export interface AuthTokenResponse {
  access_token: string
  refresh_token: string
  role: UserRole
  default_route: string
  welcome_summary?: string | null
  unfinished_session?: Record<string, unknown> | null
  onboarding_completed?: boolean
}

interface PreferenceResponse {
  user_id: number
  guidance_mode: GuidanceMode
}

interface LogoutOptions {
  redirect?: boolean
  remote?: boolean
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  refreshToken: string | null
  defaultRoute: string | null
  isLoading: boolean
  isInitialized: boolean
  login: (credentials: Credentials) => Promise<string>
  logout: (options?: LogoutOptions) => Promise<void>
  initFromStorage: () => Promise<void>
  applySession: (payload: AuthTokenResponse, email?: string) => Promise<void>
  register: (data: {
    email: string
    password: string
    full_name?: string
    role: string
    school_name: string
    teacher_id?: number
  }) => Promise<string>
  setUser: (user: AuthUser) => void
}

export const AUTH_STORAGE_KEYS = {
  accessToken: 'rmos_access_token',
  refreshToken: 'rmos_refresh_token',
  role: 'rmos_role',
  defaultRoute: 'rmos_default_route',
  email: 'rmos_user_email',
  onboardingCompleted: 'rmos_onboarding_completed',
  legacyAccessToken: 'access_token',
  legacyRefreshToken: 'refresh_token',
} as const

const authHttp = axios.create({
  baseURL: API_ROOT,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

function isUserRole(value: string | null): value is UserRole {
  return value === 'student' || value === 'teacher' || value === 'admin'
}

function persistSession(payload: AuthTokenResponse, email?: string) {
  localStorage.setItem(AUTH_STORAGE_KEYS.accessToken, payload.access_token)
  localStorage.setItem(AUTH_STORAGE_KEYS.refreshToken, payload.refresh_token)
  localStorage.setItem(AUTH_STORAGE_KEYS.role, payload.role)
  localStorage.setItem(AUTH_STORAGE_KEYS.defaultRoute, payload.default_route)
  localStorage.setItem(AUTH_STORAGE_KEYS.legacyAccessToken, payload.access_token)
  localStorage.setItem(AUTH_STORAGE_KEYS.legacyRefreshToken, payload.refresh_token)

  if (email) {
    localStorage.setItem(AUTH_STORAGE_KEYS.email, email)
  }
  localStorage.setItem(AUTH_STORAGE_KEYS.onboardingCompleted, String(payload.onboarding_completed ?? true))
}

function clearSessionStorage() {
  localStorage.removeItem(AUTH_STORAGE_KEYS.accessToken)
  localStorage.removeItem(AUTH_STORAGE_KEYS.refreshToken)
  localStorage.removeItem(AUTH_STORAGE_KEYS.role)
  localStorage.removeItem(AUTH_STORAGE_KEYS.defaultRoute)
  localStorage.removeItem(AUTH_STORAGE_KEYS.email)
  localStorage.removeItem(AUTH_STORAGE_KEYS.onboardingCompleted)
  localStorage.removeItem(AUTH_STORAGE_KEYS.legacyAccessToken)
  localStorage.removeItem(AUTH_STORAGE_KEYS.legacyRefreshToken)
}

function getStoredAccessToken() {
  return (
    localStorage.getItem(AUTH_STORAGE_KEYS.accessToken) ??
    localStorage.getItem(AUTH_STORAGE_KEYS.legacyAccessToken)
  )
}

function getStoredRefreshToken() {
  return (
    localStorage.getItem(AUTH_STORAGE_KEYS.refreshToken) ??
    localStorage.getItem(AUTH_STORAGE_KEYS.legacyRefreshToken)
  )
}

function readStoredSession() {
  const accessToken = getStoredAccessToken()
  const refreshToken = getStoredRefreshToken()
  const role = localStorage.getItem(AUTH_STORAGE_KEYS.role)
  const defaultRoute = localStorage.getItem(AUTH_STORAGE_KEYS.defaultRoute)
  const email = localStorage.getItem(AUTH_STORAGE_KEYS.email) ?? undefined
  const onboardingCompleted = localStorage.getItem(AUTH_STORAGE_KEYS.onboardingCompleted)

  if (!accessToken || !refreshToken || !isUserRole(role) || !defaultRoute) {
    return null
  }

  return {
    accessToken,
    refreshToken,
    role,
    defaultRoute,
    email,
    onboardingCompleted: onboardingCompleted !== 'false',
  }
}

async function fetchPreference(accessToken: string): Promise<{ preference: PreferenceResponse | null; newToken?: string; authExpired?: boolean }> {
  try {
    const response = await authHttp.get<PreferenceResponse>('/agent/preference', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    })
    return { preference: response.data }
  } catch (err: any) {
    if (err?.response?.status === 401) {
      // Token expired — try refreshing
      const refreshToken = getStoredRefreshToken()
      if (refreshToken) {
        try {
          const refreshRes = await authHttp.post<AuthTokenResponse>('/auth/refresh', {
            refresh_token: refreshToken,
          })
          const newToken = refreshRes.data.access_token
          // Persist the new tokens
          persistSession(refreshRes.data, localStorage.getItem(AUTH_STORAGE_KEYS.email) ?? undefined)
          // Retry preference with new token
          const retryRes = await authHttp.get<PreferenceResponse>('/agent/preference', {
            headers: { Authorization: `Bearer ${newToken}` },
          })
          return { preference: retryRes.data, newToken }
        } catch {
          // Both access token and refresh token are invalid
          return { preference: null, authExpired: true }
        }
      }
      // No refresh token available
      return { preference: null, authExpired: true }
    }
    return { preference: null }
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  defaultRoute: null,
  isLoading: false,
  isInitialized: false,
  async applySession(payload, email) {
    persistSession(payload, email)

    const baseUser: AuthUser = {
      email: email ?? localStorage.getItem(AUTH_STORAGE_KEYS.email) ?? undefined,
      role: payload.role,
      welcome_summary: payload.welcome_summary ?? null,
      unfinished_session: payload.unfinished_session ?? null,
      onboarding_completed: payload.onboarding_completed ?? true,
    }

    set({
      user: baseUser,
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      defaultRoute: payload.default_route,
      isInitialized: true,
    })

    const { preference, newToken } = await fetchPreference(payload.access_token)
    if (newToken) {
      set({ accessToken: newToken })
    }
    if (preference) {
      set((state) => ({
        user: state.user
          ? {
              ...state.user,
              user_id: preference.user_id,
              guidance_mode: preference.guidance_mode,
            }
          : state.user,
      }))
    }
  },
  async login(credentials) {
    set({ isLoading: true })

    try {
      const response = await authHttp.post<AuthTokenResponse>('/auth/login', credentials)
      await get().applySession(response.data, credentials.email)
      return response.data.default_route
    } finally {
      set({ isLoading: false })
    }
  },
  async register(data) {
    set({ isLoading: true })
    try {
      const response = await authHttp.post('/auth/register', data)
      const payload = response.data
      await get().applySession(payload, data.email)
      return payload.default_route
    } finally {
      set({ isLoading: false })
    }
  },
  setUser(user) {
    set({ user })
  },
  async logout(options) {
    const shouldRedirect = options?.redirect !== false
    const shouldRemoteLogout = options?.remote !== false
    const refreshToken = get().refreshToken ?? getStoredRefreshToken()

    if (shouldRemoteLogout && refreshToken) {
      try {
        await authHttp.post('/auth/logout', { refresh_token: refreshToken })
      } catch {
        // Best-effort remote revocation.
      }
    }

    clearSessionStorage()
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      defaultRoute: null,
      isLoading: false,
      isInitialized: true,
    })

    if (shouldRedirect && typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.assign('/login')
    }
  },
  async initFromStorage() {
    set({ isLoading: true })

    try {
      const stored = readStoredSession()
      if (!stored) {
        clearSessionStorage()
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          defaultRoute: null,
          isInitialized: true,
        })
        return
      }

      persistSession(
        {
          access_token: stored.accessToken,
          refresh_token: stored.refreshToken,
          role: stored.role,
          default_route: stored.defaultRoute,
        },
        stored.email,
      )

      set({
        user: {
          email: stored.email,
          role: stored.role,
          onboarding_completed: stored.onboardingCompleted,
        },
        accessToken: stored.accessToken,
        refreshToken: stored.refreshToken,
        defaultRoute: stored.defaultRoute,
        isInitialized: true,
      })

      const { preference, newToken, authExpired } = await fetchPreference(stored.accessToken)
      if (authExpired) {
        // Session is completely dead — clear everything to avoid infinite reload loop
        clearSessionStorage()
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          defaultRoute: null,
          isInitialized: true,
        })
        return
      }
      if (newToken) {
        set({ accessToken: newToken })
      }
      if (preference) {
        set((state) => ({
          user: state.user
            ? {
                ...state.user,
                user_id: preference.user_id,
                guidance_mode: preference.guidance_mode,
              }
            : state.user,
        }))
      }
    } catch {
      clearSessionStorage()
      set({
        user: null,
        accessToken: null,
        refreshToken: null,
        defaultRoute: null,
        isInitialized: true,
      })
    } finally {
      set({ isLoading: false })
    }
  },
}))
