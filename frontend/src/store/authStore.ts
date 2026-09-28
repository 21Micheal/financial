/**
 * authStore.ts — Financial System
 *
 * Changes:
 * - Restored persist (localStorage) so tokens survive tab duplication / refresh.
 * - Added idToken: persisted for use as id_token_hint on Keycloak logout.
 * - Removed apiClient import (circular dep). Backend logout (blacklist) must be
 *   called by the component BEFORE invoking logout() + oidcLogout().
 * - Added _hasHydrated flag so AuthBootstrap can wait for rehydration.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  organization_id?: string
  is_staff: boolean
  is_superuser: boolean
  must_change_password: boolean
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  idToken: string | null          // stored for id_token_hint on KC logout
  isAuthenticated: boolean
  _hasHydrated: boolean
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  setIdToken: (token: string | null) => void
  _setHasHydrated: (v: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      idToken: null,
      isAuthenticated: false,
      _hasHydrated: false,
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh, isAuthenticated: true }),
      setUser:    (user)  => set({ user }),
      setIdToken: (token) => set({ idToken: token }),
      _setHasHydrated: (v) => set({ _hasHydrated: v }),
      logout: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          idToken: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'financial-auth',
      onRehydrateStorage: () => (state) => {
        // Signal that persisted state has been loaded. AuthBootstrap waits for this.
        state?._setHasHydrated(true)
      },
    }
  )
)
