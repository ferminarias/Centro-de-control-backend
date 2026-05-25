import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/api/prode/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Credenciales incorrectas')
      }

      const data = await res.json()
      localStorage.setItem('prode_token', data.access_token)
      navigate(data.user.must_change_password ? '/change-password' : '/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-bg-base flex flex-col items-center justify-center px-4 animate-fade-in gap-4">
      {/* Background glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 55% 45% at 50% 0%, rgba(25,70,227,0.18) 0%, transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-sm animate-slide-up">
        {/* Card */}
        <div className="card p-8">
          <div className="flex flex-col items-center mb-8">
            <img
              src="/logo-nods.png"
              alt="Grupo Nods"
              className="h-12 w-auto object-contain mb-5"
            />
            <div className="w-full h-px bg-border mb-6" />
            <h1 className="text-xl font-mori font-semibold text-content-primary tracking-tight text-center">
              Prode Mundial 2026
            </h1>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="label">Email</label>
                <input
                  id="email"
                  type="email"
                  className="input-field"
                  placeholder="tu@gruponods.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="label">Contraseña</label>
                <input
                  id="password"
                  type="password"
                  className="input-field"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2.5">
                <AlertIcon />
                <p className="text-xs font-mori text-red-400">{error}</p>
              </div>
            )}

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <SpinnerIcon />
                  Ingresando...
                </span>
              ) : (
                'Iniciar sesión'
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-[11px] font-mori text-content-muted mt-5">
          © {new Date().getFullYear()} Grupo Nods · Uso interno
        </p>
      </div>

      {/* PWA install prompt */}
      <PWAInstallBanner />
    </div>
  )
}

// ── PWA Install Banner ────────────────────────────────────────────────────────

function PWAInstallBanner() {
  const [deferredPrompt, setDeferredPrompt] = useState<Event & { prompt: () => void; userChoice: Promise<{ outcome: string }> } | null>(null)
  const [visible, setVisible] = useState(false)
  const [showIOSGuide, setShowIOSGuide] = useState(false)
  const dismissed = localStorage.getItem('pwa_dismissed') === '1'

  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as unknown as { standalone?: boolean }).standalone === true

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent.toLowerCase())

  useEffect(() => {
    if (isStandalone || dismissed) return

    if (isIOS) {
      setVisible(true)
      return
    }

    function handler(e: Event) {
      e.preventDefault()
      setDeferredPrompt(e as typeof deferredPrompt)
      setVisible(true)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, []) // eslint-disable-line

  function dismiss() {
    localStorage.setItem('pwa_dismissed', '1')
    setVisible(false)
    setShowIOSGuide(false)
  }

  async function handleAndroidInstall() {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') setVisible(false)
    setDeferredPrompt(null)
  }

  if (!visible || isStandalone || dismissed) return null

  return (
    <>
      {/* Banner */}
      <div className="relative w-full max-w-sm animate-slide-up">
        <div className="card px-4 py-3 flex items-center gap-3 border-accent/20">
          <div className="w-9 h-9 rounded-xl bg-bg-elevated border border-border flex items-center justify-center shrink-0">
            <img src="/pwa-192.png" alt="" className="w-6 h-6 rounded-md" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-content-primary leading-tight">Instalar Prode Nods</p>
            <p className="text-[11px] text-content-muted">Accedé rápido desde la pantalla de inicio</p>
          </div>
          {isIOS ? (
            <button
              onClick={() => setShowIOSGuide(true)}
              className="shrink-0 text-xs font-semibold text-accent bg-accent/10 hover:bg-accent/20 px-3 py-1.5 rounded-lg transition-colors"
            >
              Cómo
            </button>
          ) : (
            <button
              onClick={handleAndroidInstall}
              className="shrink-0 text-xs font-semibold text-accent bg-accent/10 hover:bg-accent/20 px-3 py-1.5 rounded-lg transition-colors"
            >
              Instalar
            </button>
          )}
          <button onClick={dismiss} className="shrink-0 text-content-muted hover:text-content-primary transition-colors ml-1">
            <IconX />
          </button>
        </div>
      </div>

      {/* iOS step-by-step guide */}
      {showIOSGuide && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-end justify-center p-4 animate-fade-in" onClick={() => setShowIOSGuide(false)}>
          <div className="w-full max-w-sm card p-6 animate-slide-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <p className="text-base font-semibold text-content-primary">Instalar Prode Nods</p>
              <button onClick={() => setShowIOSGuide(false)} className="text-content-muted hover:text-content-primary">
                <IconX />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              {/* Step 1 */}
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">1</div>
                <div>
                  <p className="text-sm text-content-primary font-medium">Tocá el botón compartir</p>
                  <p className="text-xs text-content-muted mt-0.5">El ícono de la barra inferior de Safari</p>
                  <div className="mt-2 inline-flex items-center gap-1.5 bg-bg-elevated border border-border rounded-lg px-3 py-1.5">
                    <IconIOSShare />
                    <span className="text-xs text-content-secondary">Compartir</span>
                  </div>
                </div>
              </div>

              <div className="h-px bg-border" />

              {/* Step 2 */}
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">2</div>
                <div>
                  <p className="text-sm text-content-primary font-medium">Elegí "Agregar a inicio"</p>
                  <p className="text-xs text-content-muted mt-0.5">Buscá esta opción en el menú</p>
                  <div className="mt-2 inline-flex items-center gap-1.5 bg-bg-elevated border border-border rounded-lg px-3 py-1.5">
                    <IconIOSAdd />
                    <span className="text-xs text-content-secondary">Agregar a pantalla de inicio</span>
                  </div>
                </div>
              </div>

              <div className="h-px bg-border" />

              {/* Step 3 */}
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">3</div>
                <div>
                  <p className="text-sm text-content-primary font-medium">Tocá "Agregar"</p>
                  <p className="text-xs text-content-muted mt-0.5">La app aparece en tu pantalla de inicio</p>
                </div>
              </div>
            </div>

            <button
              onClick={dismiss}
              className="w-full mt-6 text-xs text-content-muted hover:text-content-primary transition-colors"
            >
              No mostrar de nuevo
            </button>
          </div>
        </div>
      )}
    </>
  )
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function AlertIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="shrink-0">
      <circle cx="7" cy="7" r="5.5" stroke="#EF4444" strokeWidth="1.2" />
      <path d="M7 4.5v3M7 9.5v.3" stroke="#EF4444" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function IconX() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function IconIOSShare() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M8 1v9M5 4l3-3 3 3" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 8v5.5a.5.5 0 00.5.5h9a.5.5 0 00.5-.5V8" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function IconIOSAdd() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1.5" y="1.5" width="13" height="13" rx="3" stroke="#1946E3" strokeWidth="1.4" />
      <path d="M8 5v6M5 8h6" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
