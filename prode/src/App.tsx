import { API } from './lib/api'
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ChangePassword from './pages/ChangePassword'
import Admin from './pages/Admin'
import Register from './pages/Register'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('prode_token')
  return token ? <>{children}</> : <Navigate to="/" replace />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('prode_token')
  const [status, setStatus] = useState<'checking' | 'ok' | 'unauth' | 'forbidden'>('checking')

  useEffect(() => {
    if (!token) { setStatus('unauth'); return }
    fetch(API + '/api/prode/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) { setStatus(r.status === 401 ? 'unauth' : 'forbidden'); return }
        return r.json()
      })
      .then(data => {
        if (!data) return
        setStatus(data.is_admin ? 'ok' : 'forbidden')
      })
      .catch(() => setStatus('unauth'))
  }, [token])

  if (status === 'checking') {
    return (
      <div className="min-h-dvh flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (status === 'unauth') return <Navigate to="/" replace />
  if (status === 'forbidden') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/registro/:token" element={<Register />} />
        <Route path="/change-password" element={<PrivateRoute><ChangePassword /></PrivateRoute>} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
