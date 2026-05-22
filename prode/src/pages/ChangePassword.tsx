import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function ChangePassword() {
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (next !== confirm) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (next.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    if (next === 'Nodsprode') {
      setError('Debés elegir una contraseña diferente a la inicial')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('prode_token')
      const res = await fetch('/api/prode/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: current, new_password: next }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Error al cambiar contraseña')
      }

      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error inesperado')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-bg-base flex items-center justify-center px-4 animate-fade-in">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 55% 45% at 50% 0%, rgba(25,70,227,0.15) 0%, transparent 70%)' }}
      />

      <div className="relative w-full max-w-sm animate-slide-up">
        <div className="card p-8">
          {/* Header */}
          <div className="flex flex-col items-center mb-8">
            <img src="/logo-nods.png" alt="Grupo Nods" className="h-10 w-auto object-contain mb-5" />
            <div className="w-full h-px bg-border mb-6" />
            <div className="text-center">
              <h1 className="text-lg font-mori font-semibold text-content-primary tracking-tight mb-1">
                Creá tu contraseña
              </h1>
              <p className="text-sm text-content-secondary font-light">
                Elegí una contraseña personal para tu cuenta
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="label">Contraseña temporal</label>
              <input
                type="password"
                className="input-field"
                placeholder="Tu contraseña actual (Nodsprode)"
                value={current}
                onChange={e => setCurrent(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="label">Nueva contraseña</label>
              <input
                type="password"
                className="input-field"
                placeholder="Mínimo 8 caracteres"
                value={next}
                onChange={e => setNext(e.target.value)}
                required
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="label">Confirmar contraseña</label>
              <input
                type="password"
                className="input-field"
                placeholder="Repetí tu nueva contraseña"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2.5">
                <AlertIcon />
                <p className="text-xs font-mori text-red-400">{error}</p>
              </div>
            )}

            <button type="submit" className="btn-primary mt-1" disabled={loading}>
              {loading
                ? <span className="flex items-center justify-center gap-2"><Spinner />Guardando...</span>
                : 'Guardar contraseña'}
            </button>
          </form>
        </div>

        <p className="text-center text-[11px] font-mori text-content-muted mt-5">
          © {new Date().getFullYear()} Grupo Nods · Uso interno
        </p>
      </div>
    </div>
  )
}

function AlertIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="shrink-0">
      <circle cx="7" cy="7" r="5.5" stroke="#EF4444" strokeWidth="1.2" />
      <path d="M7 4.5v3M7 9.5v.3" stroke="#EF4444" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
