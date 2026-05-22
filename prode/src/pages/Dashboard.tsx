import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

interface ProdeUser {
  nombre: string
  apellido: string
  email: string
}

// Grupos del Mundial 2026 (placeholder hasta tener datos reales)
const GRUPOS_PLACEHOLDER = [
  {
    letra: 'A',
    equipos: [
      { pais: 'Qatar', bandera: '🇶🇦', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'Ecuador', bandera: '🇪🇨', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'Senegal', bandera: '🇸🇳', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'Países Bajos', bandera: '🇳🇱', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
    ],
  },
  {
    letra: 'B',
    equipos: [
      { pais: 'Inglaterra', bandera: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'Iran', bandera: '🇮🇷', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'USA', bandera: '🇺🇸', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
      { pais: 'Gales', bandera: '🏴󠁧󠁢󠁷󠁬󠁳󠁿', pts: 0, pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0 },
    ],
  },
]

const MENU_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: GridIcon },
  { id: 'fixture', label: 'Fixture', icon: CalendarIcon },
  { id: 'mis-pronos', label: 'Mis Pronósticos', icon: PenIcon },
  { id: 'posiciones', label: 'Posiciones', icon: TrophyIcon },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState<ProdeUser | null>(null)
  const [activeMenu, setActiveMenu] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('prode_token')
    if (!token) {
      navigate('/')
      return
    }

    fetch('/api/prode/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => {
        if (!r.ok) throw new Error()
        return r.json()
      })
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('prode_token')
        navigate('/')
      })
  }, [navigate])

  function handleLogout() {
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
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 h-full w-60 bg-bg-surface border-r border-border z-30
          flex flex-col transition-transform duration-300 lg:translate-x-0 lg:static lg:z-auto
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="px-5 py-6 border-b border-border">
          <div className="flex items-center gap-3">
            {/* Placeholder logo — reemplazar con <img> */}
            <div className="w-8 h-8 rounded-lg bg-bg-elevated border border-border flex items-center justify-center shrink-0">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="#4ADE80" strokeWidth="1.5" />
                <path d="M8 12l2.5 2.5L16 9" stroke="#4ADE80" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold tracking-[0.15em] uppercase text-content-muted leading-none mb-0.5">
                Grupo Nods
              </p>
              <p className="text-sm font-semibold text-content-primary leading-none">
                Prode 2026
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 flex flex-col gap-0.5">
          {MENU_ITEMS.map(item => {
            const Icon = item.icon
            const active = activeMenu === item.id
            return (
              <button
                key={item.id}
                onClick={() => { setActiveMenu(item.id); setSidebarOpen(false) }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm
                  transition-all duration-150 text-left
                  ${active
                    ? 'bg-accent-subtle text-accent font-semibold'
                    : 'text-content-secondary hover:text-content-primary hover:bg-bg-elevated font-normal'
                  }
                `}
              >
                <Icon size={16} active={active} />
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* User & logout */}
        <div className="px-3 py-4 border-t border-border">
          <div className="px-3 py-2.5 rounded-lg flex items-center gap-3">
            <div className="w-7 h-7 rounded-full bg-bg-elevated border border-border flex items-center justify-center shrink-0">
              <span className="text-xs font-semibold text-content-secondary">
                {user.nombre[0]}{user.apellido[0]}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-content-primary truncate leading-tight">
                {user.nombre} {user.apellido}
              </p>
              <p className="text-[11px] text-content-muted truncate leading-tight">
                {user.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full mt-1 flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-content-muted hover:text-status-loss hover:bg-red-500/5 transition-all duration-150"
          >
            <LogoutIcon size={15} />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-border bg-bg-base flex items-center px-4 lg:px-6 gap-4 shrink-0">
          <button
            className="lg:hidden p-1.5 rounded-lg text-content-secondary hover:text-content-primary hover:bg-bg-elevated transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M2 4h14M2 9h14M2 14h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>

          <div className="flex-1">
            <h2 className="text-sm font-semibold text-content-primary">
              {MENU_ITEMS.find(m => m.id === activeMenu)?.label ?? 'Dashboard'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 bg-accent-subtle border border-accent-border rounded-full px-2.5 py-1 text-xs font-semibold text-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-soft" />
              En vivo
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {activeMenu === 'dashboard' && <HomeContent user={user} />}
          {activeMenu === 'fixture' && <PlaceholderContent title="Fixture" description="Próximos partidos del Mundial 2026" />}
          {activeMenu === 'mis-pronos' && <PlaceholderContent title="Mis Pronósticos" description="Ingresá tus predicciones para cada partido" />}
          {activeMenu === 'posiciones' && <PlaceholderContent title="Posiciones" description="Tabla de líderes del prode" />}
        </main>
      </div>
    </div>
  )
}

function HomeContent({ user }: { user: ProdeUser }) {
  return (
    <div className="flex flex-col gap-6 animate-slide-up">
      {/* Welcome */}
      <div>
        <h1 className="text-xl font-semibold text-content-primary">
          Hola, {user.nombre} 👋
        </h1>
        <p className="text-sm text-content-secondary mt-0.5">
          Mundial 2026 · USA / México / Canadá
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Pronósticos', value: '0 / 0', sub: 'partidos' },
          { label: 'Puntos', value: '0', sub: 'pts totales' },
          { label: 'Posición', value: '—', sub: 'en el ranking' },
          { label: 'Racha', value: '—', sub: 'últimos 5' },
        ].map(stat => (
          <div key={stat.label} className="card p-4">
            <p className="label mb-2">{stat.label}</p>
            <p className="text-2xl font-semibold text-content-primary leading-none mb-0.5">
              {stat.value}
            </p>
            <p className="text-xs text-content-muted">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Próximo partido highlight */}
      <div>
        <p className="label mb-3">Próximo partido</p>
        <div className="card card-hover p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4 flex-1">
              <div className="text-center flex-1">
                <p className="text-3xl mb-1">🇺🇸</p>
                <p className="text-sm font-semibold text-content-primary">USA</p>
              </div>
              <div className="text-center px-4">
                <p className="text-xs font-semibold text-content-muted uppercase tracking-wider mb-1">VS</p>
                <p className="text-[10px] text-content-muted">Grupo B · J1</p>
              </div>
              <div className="text-center flex-1">
                <p className="text-3xl mb-1">🏴󠁧󠁢󠁥󠁮󠁧󠁿</p>
                <p className="text-sm font-semibold text-content-primary">Inglaterra</p>
              </div>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs font-semibold text-content-muted">Jun 12, 2026</p>
              <p className="text-xs text-content-muted mt-0.5">MetLife Stadium</p>
              <button className="mt-3 px-3 py-1.5 rounded-lg bg-accent-subtle border border-accent-border text-accent text-xs font-semibold hover:bg-accent/15 transition-colors">
                Pronosticar
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabla de grupos placeholder */}
      <div>
        <p className="label mb-3">Grupos</p>
        <div className="grid lg:grid-cols-2 gap-3">
          {GRUPOS_PLACEHOLDER.map(grupo => (
            <div key={grupo.letra} className="card">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-sm font-semibold text-content-primary">Grupo {grupo.letra}</p>
              </div>
              <div className="divide-y divide-border">
                {grupo.equipos.map((eq, i) => (
                  <div key={eq.pais} className="px-4 py-2.5 flex items-center gap-3">
                    <span className="text-xs text-content-muted w-4">{i + 1}</span>
                    <span className="text-base">{eq.bandera}</span>
                    <span className="flex-1 text-sm text-content-primary">{eq.pais}</span>
                    <div className="flex gap-4 text-xs text-content-secondary font-medium">
                      <span title="Puntos" className="w-4 text-right">{eq.pts}</span>
                      <span title="PJ" className="w-4 text-right text-content-muted">{eq.pj}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PlaceholderContent({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3 animate-fade-in">
      <div className="w-12 h-12 rounded-xl bg-bg-surface border border-border flex items-center justify-center">
        <span className="text-2xl">⚽</span>
      </div>
      <h2 className="text-lg font-semibold text-content-primary">{title}</h2>
      <p className="text-sm text-content-secondary text-center max-w-xs">{description}</p>
      <p className="text-xs text-content-muted">Próximamente</p>
    </div>
  )
}

// Icon components
function GridIcon({ size, active }: { size: number; active: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="1" y="1" width="6" height="6" rx="1.5" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
      <rect x="9" y="1" width="6" height="6" rx="1.5" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
      <rect x="1" y="9" width="6" height="6" rx="1.5" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
      <rect x="9" y="9" width="6" height="6" rx="1.5" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
    </svg>
  )
}

function CalendarIcon({ size, active }: { size: number; active: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <rect x="1.5" y="2.5" width="13" height="12" rx="2" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
      <path d="M5 1v3M11 1v3M1.5 6.5h13" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function PenIcon({ size, active }: { size: number; active: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M11 2l3 3-8.5 8.5L2 14l.5-3.5L11 2z" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  )
}

function TrophyIcon({ size, active }: { size: number; active: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M8 11v3M5 14h6" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" strokeLinecap="round" />
      <path d="M3 2h10v5a5 5 0 01-10 0V2z" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" />
      <path d="M3 4H1v2a2 2 0 002 2M13 4h2v2a2 2 0 01-2 2" stroke={active ? '#4ADE80' : 'currentColor'} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

function LogoutIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <path d="M6 2H2v12h4M11 5l3 3-3 3M14 8H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
