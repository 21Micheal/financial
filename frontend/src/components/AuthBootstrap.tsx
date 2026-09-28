/**
 * AuthBootstrap — Financial System
 *
 * Waits for Zustand persist rehydration BEFORE evaluating auth state.
 * Without this, every tab open / page refresh sees null tokens for one render
 * cycle and RequireAuth redirects to /login before localStorage is applied.
 */
import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  // hasHydrated() is synchronously true if the store already loaded (e.g. re-render);
  // false on the very first render of a new tab before localStorage is read.
  const [hydrated, setHydrated] = useState(() => useAuthStore.persist.hasHydrated())

  const accessToken = useAuthStore((s) => s.accessToken)
  const user        = useAuthStore((s) => s.user)
  const setUser     = useAuthStore((s) => s.setUser)
  const logout      = useAuthStore((s) => s.logout)
  const [ready, setReady] = useState(false)

  // Step 1: wait for Zustand to read localStorage
  useEffect(() => {
    if (hydrated) return
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    return unsub
  }, [hydrated])

  // Step 2: once hydrated, validate the stored token
  useEffect(() => {
    if (!hydrated) return

    if (!accessToken) { setReady(true); return }
    if (user)         { setReady(true); return }

    let cancelled = false
    authAPI.me(accessToken)
      .then(({ data }) => { if (!cancelled) setUser(data) })
      .catch(()        => { if (!cancelled) logout() })
      .finally(()      => { if (!cancelled) setReady(true) })

    return () => { cancelled = true }
  }, [hydrated, accessToken, user, setUser, logout])

  if (!hydrated || !ready) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: '#0f172a',
        color: '#94a3b8', fontSize: '0.9rem',
      }}>
        Loading…
      </div>
    )
  }

  return <>{children}</>
}
