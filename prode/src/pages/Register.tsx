import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

type Step = 'validating' | 'form' | 'success' | 'invalid'

export default function Register() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('validating')
  const [form, setForm] = useState({ nombre: '', apellido: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) { setStep('invalid'); return }
    fetch(`/api/prode/auth/invitacion/${token}`)
      .then(r => r.ok ? setStep('form') : setStep('invalid'))
      .catch(() => setStep('invalid'))
  }, [token])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirm) {
      setError('Las contraseñas no coinciden')
      return
    }
    if (form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    if (!form.nombre.trim() || !form.apellido.trim()) {
      setError('Nombre y apellido son obligatorios')
      return
    }

    setLoading(true)
    try {
      const res = await fetch('/api/prode/auth/registro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          email: form.email,
          nombre: form.nombre.trim(),
          apellido: form.apellido.trim(),
          password: form.password,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Error al enviar la solicitud')
        return
      }
      setStep('success')
    } catch {
      setError('Error de conexión. Intentá de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'validating') {
    return (
      <div className="min-h-dvh bg-bg-base flex items-center justify-center font-mori">
        <div className="flex flex-col items-center gap-3 text-content-muted">
          <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Verificando invitación...</span>
        </div>
      </div>
    )
  }

  if (step === 'invalid') {
    return (
      <div className="min-h-dvh bg-bg-base flex items-center justify-center font-mori p-4">
        <div className="card w-full max-w-sm p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-red-400">
              <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="text-base font-semibold text-content-primary mb-2">Link inválido</h1>
          <p className="text-sm text-content-secondary mb-6">
            Este link de invitación no es válido o ya fue revocado. Pedile un nuevo link al administrador.
          </p>
          <button onClick={() => navigate('/')} className="btn-ghost text-sm w-full">
            Volver al inicio
          </button>
        </div>
      </div>
    )
  }

  if (step === 'success') {
    return (
      <div className="min-h-dvh bg-bg-base flex items-center justify-center font-mori p-4">
        <div className="card w-full max-w-sm p-8 text-center">
          <div className="w-12 h-12 rounded-full bg-status-win/10 flex items-center justify-center mx-auto mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-status-win">
              <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1 className="text-base font-semibold text-content-primary mb-2">¡Solicitud enviada!</h1>
          <p className="text-sm text-content-secondary mb-6">
            Tu cuenta está pendiente de aprobación. El administrador revisará tu solicitud y te avisará cuando puedas ingresar.
          </p>
          <button onClick={() => navigate('/')} className="btn-ghost text-sm w-full">
            Ir al inicio de sesión
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-bg-base flex items-center justify-center font-mori p-4">
      <div className="card w-full max-w-sm p-8">
        <div className="mb-6">
          <div className="overflow-hidden mb-5" style={{ height: '22px' }}>
            <img src="/logo-nods.png" alt="NODS" style={{ height: '35px', width: 'auto' }} />
          </div>
          <h1 className="text-lg font-semibold text-content-primary">Crear cuenta</h1>
          <p className="text-sm text-content-secondary mt-1">Completá tus datos para unirte al prode</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="reg-nombre" className="label">Nombre</label>
              <input
                id="reg-nombre"
                className="input-field"
                placeholder="Juan"
                value={form.nombre}
                onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
                required
                autoFocus
                autoComplete="given-name"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="reg-apellido" className="label">Apellido</label>
              <input
                id="reg-apellido"
                className="input-field"
                placeholder="Pérez"
                value={form.apellido}
                onChange={e => setForm(f => ({ ...f, apellido: e.target.value }))}
                required
                autoComplete="family-name"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="reg-email" className="label">Email</label>
            <input
              id="reg-email"
              className="input-field"
              type="email"
              placeholder="juan@ejemplo.com"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              required
              autoComplete="email"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="reg-password" className="label">Contraseña</label>
            <input
              id="reg-password"
              className="input-field"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              required
              autoComplete="new-password"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="reg-confirm" className="label">Confirmar contraseña</label>
            <input
              id="reg-confirm"
              className="input-field"
              type="password"
              placeholder="Repetí la contraseña"
              value={form.confirm}
              onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))}
              required
              autoComplete="new-password"
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-accent hover:bg-accent-hover text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 mt-2"
          >
            {loading ? 'Enviando solicitud...' : 'Solicitar acceso'}
          </button>
        </form>

        <p className="text-xs text-content-muted text-center mt-4">
          ¿Ya tenés cuenta?{' '}
          <button onClick={() => navigate('/')} className="text-accent hover:underline">
            Iniciar sesión
          </button>
        </p>
      </div>
    </div>
  )
}
