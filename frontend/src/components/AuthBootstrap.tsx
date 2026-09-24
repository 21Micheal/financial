/**
 * AuthBootstrap — runs once on app load.
 * Rehydrates the user object from /auth/me/ if a stored access token exists.
 * The old sessionStorage break-glass relay is removed (fix #5 — replaced by
 * the /auth/break-glass React route which redeems a signed token via API).
 */
import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'

interface AuthBootstrapProps {
  children: React.ReactNode
}

export function AuthBootstrap({ children }: AuthBootstrapProps) {
  const accessToken    = useAuthStore((s) => s.accessToken)
  const user           = useAuthStore((s) => s.user)
  const setUser        = useAuthStore((s) => s.setUser)
  const logout         = useAuthStore((s) => s.logout)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!accessToken) { setReady(true); return }
    if (user)         { setReady(true); return }

    let cancelled = false
    authAPI.me(accessToken)
      .then(({ data }) => { if (!cancelled) setUser(data) })
      .catch(() =>        { if (!cancelled) logout() })
      .finally(() =>      { if (!cancelled) setReady(true) })

    return () => { cancelled = true }
  }, [accessToken, user, setUser, logout])

  if (!ready) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        background: '#0f172a', color: '#94a3b8', fontSize: '0.9rem',
      }}>
        Loading…
      </div>
    )
  }

  return <>{children}</>
}
