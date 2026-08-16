import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import CopilotPage from './pages/CopilotPage'

function ProtectedRoute({ children }) {
  const { token } = useAuth()
  return token ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { token } = useAuth()
  return token ? <Navigate to="/ai-copilot" replace /> : children
}

export default function App() {
  return (
    <AuthProvider>
      <div className="app-bg" />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/ai-copilot" element={<ProtectedRoute><CopilotPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/ai-copilot" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
