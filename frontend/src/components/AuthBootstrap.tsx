import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'

interface AuthBootstrapProps {
  children: React.ReactNode
}

export function AuthBootstrap({ children }: AuthBootstrapProps) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const setTokens = useAuthStore((s) => s.setTokens)
  const logout = useAuthStore((s) => s.logout)
  const [ready, setReady] = useState(false)
  const [breakGlassProcessed, setBreakGlassProcessed] = useState(false)

  // Handle break-glass login from special admin route
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.has('break_glass') && !breakGlassProcessed) {
      const access = sessionStorage.getItem('break_glass_access')
      const refresh = sessionStorage.getItem('break_glass_refresh')
      const userStr = sessionStorage.getItem('break_glass_user')
      
      if (access && refresh && userStr) {
        try {
          const userData = JSON.parse(userStr)
          setTokens(access, refresh)
          setUser(userData)
          // Clean up
          sessionStorage.removeItem('break_glass_access')
          sessionStorage.removeItem('break_glass_refresh')
          sessionStorage.removeItem('break_glass_user')
          // Remove the flag from URL
          window.history.replaceState({}, '', window.location.pathname)
          console.log('Break-glass login processed successfully')
          setBreakGlassProcessed(true)
          setReady(true)
        } catch (e) {
          console.error('Failed to process break-glass login:', e)
          logout()
          setBreakGlassProcessed(true)
          setReady(true)
        }
      } else {
        setBreakGlassProcessed(true)
        setReady(true)
      }
    }
  }, [setTokens, setUser, logout, breakGlassProcessed, setReady])

  useEffect(() => {
    // Skip normal auth validation if break-glass was processed
    if (breakGlassProcessed) {
      return () => {}
    }

    let cancelled = false

    if (!accessToken) {
      setReady(true)
      return () => {
        cancelled = true
      }
    }

    if (user) {
      setReady(true)
      return () => {
        cancelled = true
      }
    }

    setReady(false)
    authAPI
      .me(accessToken)
      .then(({ data }) => {
        if (!cancelled) {
          setUser(data)
        }
      })
      .catch(() => {
        if (!cancelled) {
          logout()
        }
      })
      .finally(() => {
        if (!cancelled) {
          setReady(true)
        }
      })

    return () => {
      cancelled = true
    }
  }, [accessToken, logout, setUser, user, breakGlassProcessed])

  if (!ready) {
    return <div>Loading...</div>
  }

  return <>{children}</>
}
