import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
} from 'react'

import { useAuthStore } from '@/store/authStore'

const AuthContext = createContext({ ready: false })

export function AuthProvider({ children }: PropsWithChildren) {
  const initFromStorage = useAuthStore((state) => state.initFromStorage)
  const isInitialized = useAuthStore((state) => state.isInitialized)

  useEffect(() => {
    void initFromStorage()
  }, [initFromStorage])

  return <AuthContext.Provider value={{ ready: isInitialized }}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  return useContext(AuthContext)
}
