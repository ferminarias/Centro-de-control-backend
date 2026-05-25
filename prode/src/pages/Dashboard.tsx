import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as Flags from 'country-flag-icons/react/3x2'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ProdeUser {
  id: string
  nombre: string
  apellido: string
  email: string
  is_admin: boolean
  must_change_password: boolean
}

interface Equipo {
  id: number
  nombre: string
  codigo_iso: string
  grupo: string
}

interface Prediccion {
  id: string
  partido_id: number
  goles_local: number
  goles_visitante: number
  puntos: number | null
  updated_at: string
}

interface Partido {
  id: number
  equipo_local: Equipo | null
  equipo_visitante: Equipo | null
  fecha: string
  estadio: string | null
  fase: string
  grupo: string | null
  jornada: number | null
  goles_local: number | null
  goles_visitante: number | null
  estado: string
  mi_prediccion: Prediccion | null
}

interface TablaEntry {
  posicion: number
  user_id: string
  nombre: string
  apellido: string
  puntos: number
  exactos: number
  resultados: number
  predicciones: number
}

// ── Constants ─────────────────────────────────────────────────────────────────

const GRUPOS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']

const FASE_LABEL: Record<string, string> = {
  grupo: 'Fase de Grupos',
  r32: 'Ronda de 32',
  r16: 'Octavos de Final',
  cuartos: 'Cuartos de Final',
  semis: 'Semifinales',
  tercero: 'Tercer Puesto',
  final: 'Final',
}

const NAV = [
  { id: 'dashboard', label: 'Dashboard', Icon: IconGrid },
  { id: 'fixture', label: 'Fixture', Icon: IconCalendar },
  { id: 'mis-pronos', label: 'Mis Pronósticos', Icon: IconPen },
  { id: 'posiciones', label: 'Posiciones', Icon: IconTrophy },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function Flag({ codigo, className }: { codigo: string; className?: string }) {
  const FlagComp = (Flags as Record<string, React.ComponentType<{ className?: string }>>)[codigo]
  if (!FlagComp) return <span className={`inline-block bg-border rounded-sm ${className ?? 'w-5'}`} />
  return <FlagComp className={className ?? 'w-5 rounded-sm'} />
}

function formatFecha(iso: string) {
  const d = new Date(iso)
  return {
    date: d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' }),
    time: d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }),
  }
}

function resultadoLabel(partido: Partido): string {
  if (partido.estado !== 'finalizado') return ''
  const l = partido.goles_local ?? 0
  const v = partido.goles_visitante ?? 0
  return `${l} - ${v}`
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState<ProdeUser | null>(null)
  const [active, setActive] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('prode_token')
    if (!token) { navigate('/'); return }

    fetch('/api/prode/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then((data: ProdeUser) => {
        if (data.must_change_password) { navigate('/change-password'); return }
        setUser(data)
      })
      .catch(() => { localStorage.removeItem('prode_token'); navigate('/') })
  }, [navigate])

  function logout() {
    localStorage.removeItem('prode_token')
    navigate('/')
  }

  if (!user) {
    return (
      <div className="min-h-dvh bg-bg-base flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-bg-base flex font-mori animate-fade-in">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/70 z-20 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 h-full w-56 bg-bg-surface border-r border-border z-30
        flex flex-col transition-transform duration-300
        lg:translate-x-0 lg:static lg:z-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="px-4 py-5 border-b border-border">
          <div className="flex flex-col gap-2">
            <div className="overflow-hidden" style={{ height: '32px' }}>
              <img src="/logo-nods.png" alt="NODS" style={{ height: '46px', width: 'auto' }} />
            </div>
            <p className="text-[10px] font-semibold text-content-muted tracking-widest uppercase leading-none">
              Prode 2026
            </p>
          </div>
        </div>

        <nav className="flex-1 px-2 py-3 flex flex-col gap-0.5">
          {NAV.map(({ id, label, Icon }) => {
            const isActive = active === id
            return (
              <button
                key={id}
                onClick={() => { setActive(id); setSidebarOpen(false) }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-left
                  transition-all duration-150
                  ${isActive
                    ? 'bg-accent-subtle text-accent font-semibold'
                    : 'text-content-secondary hover:text-content-primary hover:bg-bg-elevated'
                  }
                `}
              >
                <Icon active={isActive} />
                {label}
              </button>
            )
          })}
        </nav>

        <div className="px-2 py-3 border-t border-border">
          <div className="px-3 py-2 rounded-lg flex items-center gap-3">
            <div className="w-7 h-7 rounded-full bg-bg-elevated border border-border flex items-center justify-center shrink-0">
              <span className="text-[11px] font-semibold text-content-secondary">
                {user.nombre[0]}{user.apellido[0]}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-content-primary truncate leading-tight">
                {user.nombre} {user.apellido}
              </p>
              <p className="text-[11px] text-content-muted truncate">{user.email}</p>
            </div>
          </div>
          {user.is_admin && (
            <button
              onClick={() => navigate('/admin')}
              className="w-full mt-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-content-muted hover:text-content-primary hover:bg-bg-elevated transition-all duration-150"
            >
              <IconAdmin />
              Panel admin
            </button>
          )}
          <button
            onClick={logout}
            className="w-full mt-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-content-muted hover:text-red-400 hover:bg-red-500/5 transition-all duration-150"
          >
            <IconLogout />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-border bg-bg-base flex items-center px-4 lg:px-6 gap-4 shrink-0">
          <button
            className="lg:hidden p-1.5 rounded-lg text-content-secondary hover:text-content-primary hover:bg-bg-elevated transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <IconMenu />
          </button>
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-content-primary">
              {NAV.find(n => n.id === active)?.label ?? 'Dashboard'}
            </h2>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {active === 'dashboard' && <HomeContent user={user} onNavigate={setActive} />}
          {active === 'fixture' && <FixtureContent user={user} />}
          {active === 'mis-pronos' && <MisPronosContent user={user} />}
          {active === 'posiciones' && <TablaContent user={user} />}
        </main>
      </div>
    </div>
  )
}

// ── Home ──────────────────────────────────────────────────────────────────────

function HomeContent({ user, onNavigate }: { user: ProdeUser; onNavigate: (id: string) => void }) {
  const [partidos, setPartidos] = useState<Partido[]>([])
  const [tabla, setTabla] = useState<TablaEntry[]>([])
  const token = localStorage.getItem('prode_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetch('/api/prode/partidos', { headers }).then(r => r.json()).then(setPartidos).catch(() => {})
    fetch('/api/prode/tabla', { headers }).then(r => r.json()).then(setTabla).catch(() => {})
  }, [])

  const ahora = new Date()
  const proximos = partidos
    .filter(p => p.estado === 'programado' && new Date(p.fecha) > ahora)
    .slice(0, 3)

  const miEntrada = tabla.find(t => t.user_id === user.id)
  const totalPredecibles = partidos.filter(p => p.estado === 'programado' && new Date(p.fecha) > ahora).length
  const misPredechas = partidos.filter(p => p.mi_prediccion && p.estado === 'programado' && new Date(p.fecha) > ahora).length

  return (
    <div className="flex flex-col gap-6 animate-slide-up">
      <div>
        <h1 className="text-xl font-semibold text-content-primary">Hola, {user.nombre}</h1>
        <p className="text-sm text-content-secondary mt-0.5">Mundial 2026 · USA / México / Canadá</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Mis puntos', value: miEntrada ? String(miEntrada.puntos) : '0', sub: 'pts totales' },
          { label: 'Posición', value: miEntrada ? `#${miEntrada.posicion}` : '—', sub: `de ${tabla.length}` },
          { label: 'Pronósticos', value: `${miEntrada?.predicciones ?? 0}`, sub: 'realizados' },
          { label: 'Pendientes', value: `${totalPredecibles - misPredechas}`, sub: 'sin pronosticar' },
        ].map(stat => (
          <div key={stat.label} className="card p-4">
            <p className="label mb-2">{stat.label}</p>
            <p className="text-2xl font-semibold text-content-primary leading-none mb-0.5">{stat.value}</p>
            <p className="text-xs text-content-muted">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Próximos partidos */}
      {proximos.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="label">Próximos partidos</p>
            <button onClick={() => onNavigate('fixture')} className="text-xs text-accent hover:underline">Ver todos →</button>
          </div>
          <div className="flex flex-col gap-2">
            {proximos.map(p => (
              <PartidoCardCompact key={p.id} partido={p} />
            ))}
          </div>
        </div>
      )}

      {partidos.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-content-muted text-sm">El fixture aún no está disponible.</p>
          <p className="text-content-muted text-xs mt-1">El administrador debe sincronizar los partidos.</p>
        </div>
      )}
    </div>
  )
}

function PartidoCardCompact({ partido }: { partido: Partido }) {
  const { date, time } = formatFecha(partido.fecha)
  return (
    <div className="card p-4 flex items-center gap-4">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {partido.equipo_local && (
          <>
            <Flag codigo={partido.equipo_local.codigo_iso} className="w-5 rounded-sm shrink-0" />
            <span className="text-sm text-content-primary font-medium truncate">{partido.equipo_local.nombre}</span>
          </>
        )}
      </div>
      <div className="text-center shrink-0 px-2">
        <p className="text-[10px] font-semibold text-content-muted uppercase tracking-wider">VS</p>
        {partido.mi_prediccion && (
          <p className="text-[10px] text-accent font-semibold mt-0.5">
            {partido.mi_prediccion.goles_local}-{partido.mi_prediccion.goles_visitante}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
        <span className="text-sm text-content-primary font-medium truncate">{partido.equipo_visitante?.nombre}</span>
        {partido.equipo_visitante && (
          <Flag codigo={partido.equipo_visitante.codigo_iso} className="w-5 rounded-sm shrink-0" />
        )}
      </div>
      <div className="text-right shrink-0 border-l border-border pl-4 hidden sm:block">
        <p className="text-xs text-content-secondary capitalize">{date}</p>
        <p className="text-xs text-content-muted">{time}</p>
      </div>
    </div>
  )
}

// ── Fixture ───────────────────────────────────────────────────────────────────

function FixtureContent({ user }: { user: ProdeUser }) {
  const [partidos, setPartidos] = useState<Partido[]>([])
  const [loading, setLoading] = useState(true)
  const [grupoActivo, setGrupoActivo] = useState<string | 'eliminatorias'>('A')
  const [toast, setToast] = useState('')
  const token = localStorage.getItem('prode_token')

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const fetchPartidos = useCallback(async () => {
    try {
      const res = await fetch('/api/prode/partidos', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setPartidos(await res.json())
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { fetchPartidos() }, [fetchPartidos])

  async function savePred(partidoId: number, gl: number, gv: number) {
    const res = await fetch('/api/prode/predicciones', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ partido_id: partidoId, goles_local: gl, goles_visitante: gv }),
    })
    if (!res.ok) {
      const d = await res.json()
      showToast(d.detail || 'Error al guardar')
      return
    }
    showToast('Pronóstico guardado')
    fetchPartidos()
  }

  const isEliminatoria = (fase: string) => fase !== 'grupo'
  const grupoPartidos = grupoActivo === 'eliminatorias'
    ? partidos.filter(p => isEliminatoria(p.fase))
    : partidos.filter(p => p.grupo === grupoActivo)

  const eliminatoriasFases = ['r32', 'r16', 'cuartos', 'semis', 'tercero', 'final']

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (partidos.length === 0) {
    return (
      <div className="card p-10 text-center">
        <p className="text-content-secondary text-sm">El fixture aún no está disponible.</p>
        <p className="text-content-muted text-xs mt-1">El administrador debe sincronizar desde football-data.org.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      {/* Tabs grupos / eliminatorias */}
      <div className="flex gap-1 flex-wrap">
        {GRUPOS.map(g => (
          <button
            key={g}
            onClick={() => setGrupoActivo(g)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              grupoActivo === g
                ? 'bg-accent text-white'
                : 'bg-bg-surface text-content-muted hover:text-content-primary border border-border'
            }`}
          >
            {g}
          </button>
        ))}
        <button
          onClick={() => setGrupoActivo('eliminatorias')}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ml-1 ${
            grupoActivo === 'eliminatorias'
              ? 'bg-accent text-white'
              : 'bg-bg-surface text-content-muted hover:text-content-primary border border-border'
          }`}
        >
          Eliminatorias
        </button>
      </div>

      {/* Partidos */}
      {grupoActivo !== 'eliminatorias' ? (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-sm font-semibold text-content-primary">Grupo {grupoActivo}</p>
          </div>
          {grupoPartidos.length === 0 ? (
            <p className="text-content-muted text-sm text-center py-8">Sin partidos cargados</p>
          ) : (
            <div className="divide-y divide-border">
              {grupoPartidos.map(p => (
                <PartidoRow key={p.id} partido={p} onSave={savePred} />
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {eliminatoriasFases.map(fase => {
            const fasePartidos = grupoPartidos.filter(p => p.fase === fase)
            if (fasePartidos.length === 0) return null
            return (
              <div key={fase} className="card overflow-hidden">
                <div className="px-4 py-3 border-b border-border">
                  <p className="text-sm font-semibold text-content-primary">{FASE_LABEL[fase]}</p>
                </div>
                <div className="divide-y divide-border">
                  {fasePartidos.map(p => (
                    <PartidoRow key={p.id} partido={p} onSave={savePred} />
                  ))}
                </div>
              </div>
            )
          })}
          {grupoPartidos.length === 0 && (
            <div className="card p-8 text-center">
              <p className="text-content-muted text-sm">Las eliminatorias se cargarán cuando se definan los cruces.</p>
            </div>
          )}
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-bg-elevated border border-border rounded-xl px-5 py-3 text-sm text-content-primary shadow-card-hover z-50">
          {toast}
        </div>
      )}
    </div>
  )
}

function PartidoRow({ partido, onSave }: { partido: Partido; onSave: (id: number, gl: number, gv: number) => void }) {
  const { date, time } = formatFecha(partido.fecha)
  const [gl, setGl] = useState(partido.mi_prediccion?.goles_local ?? 0)
  const [gv, setGv] = useState(partido.mi_prediccion?.goles_visitante ?? 0)
  const [saving, setSaving] = useState(false)
  const ahora = new Date()
  const cerrado = partido.estado !== 'programado' || new Date(partido.fecha) <= ahora

  useEffect(() => {
    setGl(partido.mi_prediccion?.goles_local ?? 0)
    setGv(partido.mi_prediccion?.goles_visitante ?? 0)
  }, [partido.mi_prediccion])

  async function handleSave() {
    setSaving(true)
    await onSave(partido.id, gl, gv)
    setSaving(false)
  }

  const puntosColor = partido.mi_prediccion?.puntos === 3
    ? 'text-status-win'
    : partido.mi_prediccion?.puntos === 1
      ? 'text-status-draw'
      : 'text-content-muted'

  return (
    <div className="px-4 py-4 flex items-center gap-3">
      {/* Fecha */}
      <div className="w-20 shrink-0 hidden sm:block">
        <p className="text-xs text-content-secondary capitalize leading-tight">{date}</p>
        <p className="text-xs text-content-muted">{time}</p>
      </div>

      {/* Local */}
      <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
        <span className="text-sm text-content-primary font-medium truncate text-right">
          {partido.equipo_local?.nombre ?? '?'}
        </span>
        <Flag codigo={partido.equipo_local?.codigo_iso ?? ''} className="w-6 rounded-sm shrink-0" />
      </div>

      {/* Score / Predicción */}
      <div className="shrink-0 flex flex-col items-center gap-1.5 px-2">
        {partido.estado === 'finalizado' ? (
          <div className="text-center">
            <p className="text-base font-semibold text-content-primary tabular-nums">
              {partido.goles_local} - {partido.goles_visitante}
            </p>
            {partido.mi_prediccion && (
              <p className={`text-xs font-semibold ${puntosColor}`}>
                {partido.mi_prediccion.puntos === 3
                  ? '+3 exacto'
                  : partido.mi_prediccion.puntos === 1
                    ? '+1 resultado'
                    : '0 pts'}
              </p>
            )}
            {!partido.mi_prediccion && (
              <p className="text-xs text-content-muted">sin pronós.</p>
            )}
          </div>
        ) : partido.estado === 'en_juego' ? (
          <div className="text-center">
            <span className="text-xs font-semibold text-status-draw bg-status-draw/10 px-2 py-0.5 rounded-full">
              En juego
            </span>
            {partido.mi_prediccion && (
              <p className="text-xs text-content-muted mt-1">
                {partido.mi_prediccion.goles_local}-{partido.mi_prediccion.goles_visitante}
              </p>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <ScoreInput value={gl} onChange={setGl} disabled={cerrado} />
            <span className="text-xs text-content-muted font-semibold">-</span>
            <ScoreInput value={gv} onChange={setGv} disabled={cerrado} />
            <button
              onClick={handleSave}
              disabled={saving || cerrado}
              className={`ml-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-colors ${
                partido.mi_prediccion
                  ? 'bg-bg-elevated text-content-secondary hover:bg-border border border-border'
                  : 'bg-accent text-white hover:bg-accent-hover'
              } disabled:opacity-40`}
            >
              {saving ? '...' : partido.mi_prediccion ? '✓' : 'Guardar'}
            </button>
          </div>
        )}
      </div>

      {/* Visitante */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <Flag codigo={partido.equipo_visitante?.codigo_iso ?? ''} className="w-6 rounded-sm shrink-0" />
        <span className="text-sm text-content-primary font-medium truncate">
          {partido.equipo_visitante?.nombre ?? '?'}
        </span>
      </div>

      {/* Estadio */}
      <div className="w-24 shrink-0 hidden lg:block">
        <p className="text-[11px] text-content-muted truncate">{partido.estadio ?? ''}</p>
      </div>
    </div>
  )
}

function ScoreInput({ value, onChange, disabled }: { value: number; onChange: (v: number) => void; disabled: boolean }) {
  return (
    <div className="flex flex-col items-center">
      <button
        onClick={() => onChange(Math.min(99, value + 1))}
        disabled={disabled}
        className="w-5 h-4 flex items-center justify-center text-content-muted hover:text-content-primary disabled:opacity-30 text-[10px] leading-none"
      >▲</button>
      <span className="text-base font-semibold text-content-primary tabular-nums w-5 text-center">{value}</span>
      <button
        onClick={() => onChange(Math.max(0, value - 1))}
        disabled={disabled}
        className="w-5 h-4 flex items-center justify-center text-content-muted hover:text-content-primary disabled:opacity-30 text-[10px] leading-none"
      >▼</button>
    </div>
  )
}

// ── Mis Pronósticos ───────────────────────────────────────────────────────────

function MisPronosContent({ user }: { user: ProdeUser }) {
  const [preds, setPreds] = useState<(Prediccion & { partido: Partido })[]>([])
  const [loading, setLoading] = useState(true)
  const [filtro, setFiltro] = useState<'todos' | 'pendientes' | 'jugados'>('todos')
  const token = localStorage.getItem('prode_token')

  useEffect(() => {
    fetch('/api/prode/predicciones/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(setPreds)
      .finally(() => setLoading(false))
  }, [])

  const ahora = new Date()
  const filtrados = preds.filter(p => {
    if (filtro === 'pendientes') return p.partido.estado !== 'finalizado'
    if (filtro === 'jugados') return p.partido.estado === 'finalizado'
    return true
  })

  const totalPts = preds.reduce((s, p) => s + (p.puntos ?? 0), 0)
  const exactos = preds.filter(p => p.puntos === 3).length
  const resultados = preds.filter(p => p.puntos === 1).length
  const jugados = preds.filter(p => p.partido.estado === 'finalizado').length

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Puntos totales', value: String(totalPts), sub: 'acumulados' },
          { label: 'Exactos', value: String(exactos), sub: '3 pts cada uno' },
          { label: 'Resultados', value: String(resultados), sub: '1 pt cada uno' },
          { label: 'Pronósticos', value: `${preds.length}`, sub: `${jugados} jugados` },
        ].map(s => (
          <div key={s.label} className="card p-4">
            <p className="label mb-2">{s.label}</p>
            <p className="text-2xl font-semibold text-content-primary leading-none mb-0.5">{s.value}</p>
            <p className="text-xs text-content-muted">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Filtro */}
      <div className="flex gap-1">
        {(['todos', 'pendientes', 'jugados'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFiltro(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors capitalize ${
              filtro === f
                ? 'bg-accent text-white'
                : 'bg-bg-surface text-content-muted hover:text-content-primary border border-border'
            }`}
          >
            {f === 'todos' ? 'Todos' : f === 'pendientes' ? 'Pendientes' : 'Jugados'}
          </button>
        ))}
      </div>

      {preds.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="text-content-secondary text-sm">Todavía no hiciste ningún pronóstico.</p>
          <p className="text-content-muted text-xs mt-1">Andá al Fixture y comenzá a predecir.</p>
        </div>
      ) : filtrados.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-content-muted text-sm">Sin pronósticos en este filtro.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="divide-y divide-border">
            {filtrados.map(pred => {
              const { date, time } = formatFecha(pred.partido.fecha)
              const puntosColor = pred.puntos === 3 ? 'text-status-win' : pred.puntos === 1 ? 'text-status-draw' : 'text-content-muted'
              const jugado = pred.partido.estado === 'finalizado'
              return (
                <div key={pred.id} className="px-4 py-3 flex items-center gap-3">
                  <div className="w-20 shrink-0 hidden sm:block">
                    <p className="text-xs text-content-secondary capitalize">{date}</p>
                    <p className="text-xs text-content-muted">{time}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
                    <span className="text-sm text-content-primary font-medium truncate text-right">
                      {pred.partido.equipo_local?.nombre ?? '?'}
                    </span>
                    <Flag codigo={pred.partido.equipo_local?.codigo_iso ?? ''} className="w-5 rounded-sm shrink-0" />
                  </div>
                  <div className="shrink-0 text-center px-2">
                    <p className="text-base font-semibold text-content-primary tabular-nums">
                      {pred.goles_local} - {pred.goles_visitante}
                    </p>
                    {jugado && (
                      <p className="text-[10px] text-content-muted">
                        Real: {pred.partido.goles_local}-{pred.partido.goles_visitante}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <Flag codigo={pred.partido.equipo_visitante?.codigo_iso ?? ''} className="w-5 rounded-sm shrink-0" />
                    <span className="text-sm text-content-primary font-medium truncate">
                      {pred.partido.equipo_visitante?.nombre ?? '?'}
                    </span>
                  </div>
                  <div className="w-16 shrink-0 text-right">
                    {jugado ? (
                      <span className={`text-sm font-semibold ${puntosColor}`}>
                        {pred.puntos === 3 ? '+3' : pred.puntos === 1 ? '+1' : '0'}
                        <span className="text-[10px] font-normal ml-0.5">pts</span>
                      </span>
                    ) : (
                      <span className="text-xs text-content-muted">pendiente</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tabla de Posiciones ───────────────────────────────────────────────────────

function TablaContent({ user }: { user: ProdeUser }) {
  const [tabla, setTabla] = useState<TablaEntry[]>([])
  const [loading, setLoading] = useState(true)
  const token = localStorage.getItem('prode_token')

  useEffect(() => {
    fetch('/api/prode/tabla', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(setTabla)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 animate-slide-up">
      <div>
        <h1 className="text-xl font-semibold text-content-primary">Tabla de Posiciones</h1>
        <p className="text-sm text-content-secondary mt-0.5">{tabla.length} participantes · 3 pts exacto · 1 pt resultado</p>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="label text-center px-3 py-3 w-10">#</th>
              <th className="label text-left px-4 py-3">Jugador</th>
              <th className="label text-center px-3 py-3">Pts</th>
              <th className="label text-center px-3 py-3 hidden sm:table-cell">Exactos</th>
              <th className="label text-center px-3 py-3 hidden sm:table-cell">Resultados</th>
              <th className="label text-center px-3 py-3 hidden md:table-cell">Pronós.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {tabla.map(entry => {
              const isMe = entry.user_id === user.id
              const medal = entry.posicion === 1 ? '🥇' : entry.posicion === 2 ? '🥈' : entry.posicion === 3 ? '🥉' : null
              return (
                <tr
                  key={entry.user_id}
                  className={`transition-colors ${isMe ? 'bg-accent-subtle' : 'hover:bg-bg-elevated'}`}
                >
                  <td className="px-3 py-3 text-center">
                    {medal
                      ? <span className="text-base">{medal}</span>
                      : <span className={`text-sm font-semibold ${isMe ? 'text-accent' : 'text-content-muted'}`}>{entry.posicion}</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-bg-elevated border border-border flex items-center justify-center text-[11px] font-semibold text-content-secondary shrink-0">
                        {entry.nombre[0]}{entry.apellido[0]}
                      </div>
                      <div>
                        <p className={`font-medium leading-tight ${isMe ? 'text-accent' : 'text-content-primary'}`}>
                          {entry.nombre} {entry.apellido}
                          {isMe && <span className="ml-1.5 text-[10px] font-semibold bg-accent/10 text-accent px-1.5 py-0.5 rounded-full">vos</span>}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-center">
                    <span className={`text-base font-semibold ${isMe ? 'text-accent' : 'text-content-primary'}`}>
                      {entry.puntos}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-center hidden sm:table-cell">
                    <span className="text-sm text-status-win font-medium">{entry.exactos}</span>
                  </td>
                  <td className="px-3 py-3 text-center hidden sm:table-cell">
                    <span className="text-sm text-status-draw font-medium">{entry.resultados}</span>
                  </td>
                  <td className="px-3 py-3 text-center hidden md:table-cell">
                    <span className="text-sm text-content-muted">{entry.predicciones}</span>
                  </td>
                </tr>
              )
            })}
            {tabla.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-content-muted text-sm">
                  Aún no hay puntos registrados
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconGrid({ active }: { active: boolean }) {
  const c = active ? '#1946E3' : 'currentColor'
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <rect x="1" y="1" width="5.5" height="5.5" rx="1.5" stroke={c} strokeWidth="1.2" />
      <rect x="8.5" y="1" width="5.5" height="5.5" rx="1.5" stroke={c} strokeWidth="1.2" />
      <rect x="1" y="8.5" width="5.5" height="5.5" rx="1.5" stroke={c} strokeWidth="1.2" />
      <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1.5" stroke={c} strokeWidth="1.2" />
    </svg>
  )
}
function IconCalendar({ active }: { active: boolean }) {
  const c = active ? '#1946E3' : 'currentColor'
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <rect x="1.5" y="2.5" width="12" height="11" rx="2" stroke={c} strokeWidth="1.2" />
      <path d="M5 1.5v2M10 1.5v2M1.5 6h12" stroke={c} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}
function IconPen({ active }: { active: boolean }) {
  const c = active ? '#1946E3' : 'currentColor'
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <path d="M10.5 2l2.5 2.5-7.5 7.5-3 .5.5-3L10.5 2z" stroke={c} strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  )
}
function IconTrophy({ active }: { active: boolean }) {
  const c = active ? '#1946E3' : 'currentColor'
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <path d="M7.5 10.5v3M5 13.5h5" stroke={c} strokeWidth="1.2" strokeLinecap="round" />
      <path d="M3 2h9v4.5a4.5 4.5 0 01-9 0V2z" stroke={c} strokeWidth="1.2" />
      <path d="M3 3.5H1.5v2a1.5 1.5 0 001.5 1.5M12 3.5h1.5v2a1.5 1.5 0 01-1.5 1.5" stroke={c} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}
function IconLogout() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M5.5 2H2v10h3.5M9.5 4.5l3 2.5-3 2.5M12.5 7H5.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function IconMenu() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M2 4.5h14M2 9h14M2 13.5h14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}
function IconAdmin() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="4.5" r="2.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M1.5 12c0-2.5 2.5-4 5.5-4s5.5 1.5 5.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}
