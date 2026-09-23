import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import LauncherPage from './pages/LauncherPage'
import { AuthBootstrap } from './components/AuthBootstrap'

function App() {
  return (
    <BrowserRouter>
      <AuthBootstrap>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/launcher" element={<LauncherPage />} />
          <Route path="/" element={<Navigate to="/launcher" replace />} />
        </Routes>
      </AuthBootstrap>
    </BrowserRouter>
  )
}

export default App
