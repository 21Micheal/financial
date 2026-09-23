import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { launcherAPI } from '../services/api'
import './LauncherPage.css'

interface SystemLicense {
  system: string
  system_display: string
  is_active: boolean
  user_role?: string
  user_role_display?: string
  access_granted: boolean
  access_message?: string
}

export default function LauncherPage() {
  const [systems, setSystems] = useState<SystemLicense[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null)
  const [redirecting, setRedirecting] = useState(false)

  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    const fetchSystems = async () => {
      try {
        const { data } = await launcherAPI.getLicensedSystems()
        setSystems(data.systems)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load systems')
        if (err.response?.status === 401) {
          logout()
          navigate('/login')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchSystems()
  }, [navigate, logout])

  const handleSystemClick = async (system: string) => {
    if (redirecting) return

    const systemData = systems.find(s => s.system === system)
    if (!systemData) return

    // Check if user has access
    if (!systemData.access_granted) {
      setError(systemData.access_message || 'Access denied')
      return
    }

    setSelectedSystem(system)
    setRedirecting(true)
    setError('')

    try {
      const { data } = await launcherAPI.initiateSSO(system)
      // Redirect to the SSO URL
      window.location.href = data.sso_url
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initiate SSO')
      setRedirecting(false)
      setSelectedSystem(null)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="launcher-page">
        <div className="loading">Loading systems...</div>
      </div>
    )
  }

  return (
    <div className="launcher-page">
      <header className="launcher-header">
        <div className="header-content">
          <h1>Financial System Launcher</h1>
          <div className="user-info">
            <span>{user?.first_name} {user?.last_name}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="launcher-main">
        {error && <div className="error-message">{error}</div>}

        <div className="systems-grid">
          {systems.map((system) => (
            <div
              key={system.system}
              className={`system-card ${!system.access_granted ? 'blocked' : ''} ${selectedSystem === system.system ? 'selected' : ''}`}
              onClick={() => !redirecting && handleSystemClick(system.system)}
            >
              <div className="system-icon">
                {system.system === 'dms' && '📄'}
                {system.system === 'inventory' && '📦'}
                {system.system === 'financial' && '💰'}
              </div>
              <h3>{system.system_display}</h3>
              {system.user_role ? (
                <p className="user-role">Your role: {system.user_role_display}</p>
              ) : (
                <p className="no-role">Not provisioned</p>
              )}
              {!system.access_granted && (
                <div className="access-denied">
                  {system.access_message || 'Contact your administrator for access'}
                </div>
              )}
              {redirecting && selectedSystem === system.system && (
                <div className="redirecting">Redirecting...</div>
              )}
            </div>
          ))}
        </div>

        {systems.length === 0 && !error && (
          <div className="no-systems">
            <p>No systems are currently licensed for your organization.</p>
            <p>Contact your administrator to add system licenses.</p>
          </div>
        )}
      </main>
    </div>
  )
}
