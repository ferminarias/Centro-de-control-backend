import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGoogleLogin } from '@react-oauth/google'

const GOOGLE_ENABLED = !!import.meta.env.VITE_GOOGLE_CLIENT_ID

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleLoading, setGoogleLoading] = useState(false)
  const [error, setError] = useState('')
  const [showEmailForm, setShowEmailForm] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('prode_token')
    if (!token) return
    // Validate token silently — if expired/invalid, stay on login
    fetch('/api/prode/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (r.ok) navigate('/dashboard', { replace: true }) })
      .catch(() => {})
  }, [])

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      // useGoogleLogin with flow='implicit' returns access_token, not credential
      // We need to get the ID token via the userinfo endpoint
      setGoogleLoading(true)
      setError('')
      try {
        const res = await fetch('/api/prode/auth/google-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: tokenResponse.access_token }),
        })
        if (!res.ok) {
          const d = await res.json()
          throw new Error(d.detail || 'Error al iniciar sesión con Google')
        }
        const data = await res.json()
        localStorage.setItem('prode_token', data.access_token)
        navigate(data.user.must_change_password ? '/change-password' : '/dashboard')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error con Google')
      } finally {
        setGoogleLoading(false)
      }
    },
    onError: () => setError('Error al conectar con Google'),
    flow: 'implicit',
  })

  async function handleEmailSubmit(e: React.FormEvent) {
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
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 55% 45% at 50% 0%, rgba(25,70,227,0.18) 0%, transparent 70%)',
        }}
      />

      <div className="relative w-full max-w-sm animate-slide-up">
        <div className="card p-8">
          {/* Header */}
          <div className="flex flex-col items-center mb-8">
            <img src="/logo-nods.png" alt="Grupo Nods" className="h-12 w-auto object-contain mb-5" />
            <div className="w-full h-px bg-border mb-6" />
            <h1 className="text-xl font-mori font-semibold text-content-primary tracking-tight text-center">
              Prode Mundial 2026
            </h1>
            <p className="text-xs text-content-muted mt-1 text-center">
              Ingresá con tu cuenta de Nods
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {GOOGLE_ENABLED && (
              <>
                {/* Google button */}
                <button
                  onClick={() => googleLogin()}
                  disabled={googleLoading}
                  className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-800 font-semibold text-sm py-3 px-4 rounded-xl border border-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {googleLoading ? <SpinnerIcon dark /> : <GoogleIcon />}
                  {googleLoading ? 'Conectando...' : 'Continuar con Google'}
                </button>

                {/* Divider */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-[11px] text-content-muted">o</span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              </>
            )}

            {/* Email form — collapsed by default */}
            {!showEmailForm ? (
              <button
                onClick={() => setShowEmailForm(true)}
                className="w-full text-xs text-content-muted hover:text-content-secondary transition-colors py-1"
              >
                Iniciar sesión con email y contraseña
              </button>
            ) : (
              <form onSubmit={handleEmailSubmit} className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="label">Email</label>
                  <input
                    type="email" className="input-field"
                    placeholder="tu@gruponods.com"
                    value={email} onChange={e => setEmail(e.target.value)}
                    required autoComplete="email"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="label">Contraseña</label>
                  <input
                    type="password" className="input-field"
                    placeholder="••••••••"
                    value={password} onChange={e => setPassword(e.target.value)}
                    required autoComplete="current-password"
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? <span className="flex items-center justify-center gap-2"><SpinnerIcon />Ingresando...</span> : 'Iniciar sesión'}
                </button>
              </form>
            )}

            {error && (
              <div className="flex items-center gap-2 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2.5">
                <AlertIcon />
                <p className="text-xs text-red-400">{error}</p>
              </div>
            )}
          </div>
        </div>

        <p className="text-center text-[11px] text-content-muted mt-5">
          © {new Date().getFullYear()} Grupo Nods · Uso interno
        </p>
      </div>

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
    if (isIOS) { setVisible(true); return }
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
            <button onClick={() => setShowIOSGuide(true)} className="shrink-0 text-xs font-semibold text-accent bg-accent/10 hover:bg-accent/20 px-3 py-1.5 rounded-lg transition-colors">Cómo</button>
          ) : (
            <button onClick={handleAndroidInstall} className="shrink-0 text-xs font-semibold text-accent bg-accent/10 hover:bg-accent/20 px-3 py-1.5 rounded-lg transition-colors">Instalar</button>
          )}
          <button onClick={dismiss} className="shrink-0 text-content-muted hover:text-content-primary transition-colors ml-1"><IconX /></button>
        </div>
      </div>

      {showIOSGuide && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-end justify-center p-4 animate-fade-in" onClick={() => setShowIOSGuide(false)}>
          <div className="w-full max-w-sm card p-6 animate-slide-up" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <p className="text-base font-semibold text-content-primary">Instalar Prode Nods</p>
              <button onClick={() => setShowIOSGuide(false)} className="text-content-muted hover:text-content-primary"><IconX /></button>
            </div>
            <div className="flex flex-col gap-4">
              {[
                { step: 1, title: 'Tocá el botón compartir', sub: 'El ícono en la barra de Safari', icon: <IconIOSShare /> },
                { step: 2, title: 'Elegí "Agregar a inicio"', sub: 'Buscá esta opción en el menú', icon: <IconIOSAdd /> },
                { step: 3, title: 'Tocá "Agregar"', sub: 'La app aparece en tu inicio', icon: null },
              ].map(({ step, title, sub, icon }, i) => (
                <div key={step}>
                  {i > 0 && <div className="h-px bg-border mb-4" />}
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">{step}</div>
                    <div>
                      <p className="text-sm text-content-primary font-medium">{title}</p>
                      <p className="text-xs text-content-muted mt-0.5">{sub}</p>
                      {icon && <div className="mt-2 inline-flex items-center gap-1.5 bg-bg-elevated border border-border rounded-lg px-3 py-1.5">{icon}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <button onClick={dismiss} className="w-full mt-6 text-xs text-content-muted hover:text-content-secondary transition-colors">No mostrar de nuevo</button>
          </div>
        </div>
      )}
    </>
  )
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  )
}
function AlertIcon() {
  return <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="shrink-0"><circle cx="7" cy="7" r="5.5" stroke="#EF4444" strokeWidth="1.2"/><path d="M7 4.5v3M7 9.5v.3" stroke="#EF4444" strokeWidth="1.2" strokeLinecap="round"/></svg>
}
function SpinnerIcon({ dark }: { dark?: boolean }) {
  return <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke={dark ? '#374151' : 'currentColor'} strokeWidth="3"/><path className="opacity-75" fill={dark ? '#374151' : 'currentColor'} d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
}
function IconX() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
}
function IconIOSShare() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 1v9M5 4l3-3 3 3" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M3 8v5.5a.5.5 0 00.5.5h9a.5.5 0 00.5-.5V8" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round"/></svg>
}
function IconIOSAdd() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1.5" y="1.5" width="13" height="13" rx="3" stroke="#1946E3" strokeWidth="1.4"/><path d="M8 5v6M5 8h6" stroke="#1946E3" strokeWidth="1.4" strokeLinecap="round"/></svg>
}
