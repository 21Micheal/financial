import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import LoginPage from './pages/LoginPage'
import LauncherPage from './pages/LauncherPage'
import OIDCCallbackPage from './pages/OIDCCallbackPage'
import BreakGlassRedeemPage from './pages/BreakGlassRedeemPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import { AuthBootstrap } from './components/AuthBootstrap'
import type { ReactNode } from 'react'

/** fix #10F: gate every protected route — redirects to /login when unauthenticated */
function RequireAuth({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  /** fix #7D: force password change before accessing any other page */
  if (user?.must_change_password && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <BrowserRouter>
      <AuthBootstrap>
        <Routes>
          {/* Public */}
          <Route path="/login"         element={<LoginPage />} />
          <Route path="/auth/callback" element={<OIDCCallbackPage />} />
          <Route path="/auth/break-glass" element={<BreakGlassRedeemPage />} />

          {/* Protected */}
          <Route path="/change-password" element={<RequireAuth><ChangePasswordPage /></RequireAuth>} />
          <Route path="/launcher"        element={<RequireAuth><LauncherPage /></RequireAuth>} />

          {/* Default */}
          <Route path="/" element={<Navigate to="/launcher" replace />} />
        </Routes>
      </AuthBootstrap>
    </BrowserRouter>
  )
}

export default App
