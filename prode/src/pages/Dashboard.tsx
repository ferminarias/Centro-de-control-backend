import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import * as Flags from 'country-flag-icons/react/3x2'

interface ProdeUser {
  nombre: string
  apellido: string
  email: string
}

interface Equipo {
  pais: string
  codigo: keyof typeof Flags
  pts: number
  pj: number
}

const GRUPOS: { letra: string; equipos: Equipo[] }[] = [
  {
    letra: 'A',
    equipos: [
      { pais: 'México', codigo: 'MX', pts: 0, pj: 0 },
      { pais: 'Ecuador', codigo: 'EC', pts: 0, pj: 0 },
      { pais: 'Senegal', codigo: 'SN', pts: 0, pj: 0 },
      { pais: 'Países Bajos', codigo: 'NL', pts: 0, pj: 0 },
    ],
  },
  {
    letra: 'B',
    equipos: [
      { pais: 'Inglaterra', codigo: 'GB', pts: 0, pj: 0 },
      { pais: 'Irán', codigo: 'IR', pts: 0, pj: 0 },
      { pais: 'USA', codigo: 'US', pts: 0, pj: 0 },
      { pais: 'Australia', codigo: 'AU', pts: 0, pj: 0 },
    ],
  },
]

const NAV = [
  { id: 'dashboard', label: 'Dashboard', Icon: IconGrid },
  { id: 'fixture', label: 'Fixture', Icon: IconCalendar },
  { id: 'mis-pronos', label: 'Mis Pronósticos', Icon: IconPen },
  { id: 'posiciones', label: 'Posiciones', Icon: IconTrophy },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [user, setUser] = useState<ProdeUser | null>(null)
  const [active, setActive] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('prode_token')
    if (!token) { navigate('/'); return }

    fetch('/api/prode/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setUser)
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
      {/* Mobile overlay */}
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
        {/* Logo */}
        <div className="px-4 py-5 border-b border-border">
          <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1.5">
            <img
              src="/logo-nods.png"
              alt="Grupo Nods"
              className="h-5 w-auto object-contain object-left"
            />
            <p className="text-[10px] font-semibold text-content-muted leading-none tracking-wide">
              Prode Mundial 2026
            </p>
          </div>
          </div>
        </div>

        {/* Nav */}
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

        {/* User */}
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
        {/* Header */}
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
          <div className="flex items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 bg-accent-subtle border border-accent-border rounded-full px-2.5 py-1 text-xs font-semibold text-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-soft" />
              En vivo
            </span>
          </div>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {active === 'dashboard' && <HomeContent user={user} />}
          {active !== 'dashboard' && (
            <PlaceholderContent
              title={NAV.find(n => n.id === active)?.label ?? ''}
            />
          )}
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
          Hola, {user.nombre}
        </h1>
        <p className="text-sm text-content-secondary mt-0.5">
          Mundial 2026 · USA / México / Canadá
        </p>
      </div>

      {/* Stats */}
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

      {/* Próximo partido */}
      <div>
        <p className="label mb-3">Próximo partido</p>
        <div className="card card-hover p-5">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 flex-1">
              <TeamDisplay codigo="US" nombre="USA" />
              <div className="text-center px-2">
                <p className="text-[10px] font-semibold text-content-muted uppercase tracking-wider mb-1">VS</p>
                <p className="text-[10px] text-content-muted">Grupo B · J1</p>
              </div>
              <TeamDisplay codigo="GB" nombre="Inglaterra" />
            </div>
            <div className="text-right shrink-0 border-l border-border pl-4">
              <p className="text-xs font-semibold text-content-secondary">Jun 12, 2026</p>
              <p className="text-[11px] text-content-muted mt-0.5">MetLife Stadium</p>
              <button className="mt-3 px-3 py-1.5 rounded-lg bg-accent-subtle border border-accent-border text-accent text-xs font-semibold hover:bg-accent/15 transition-colors">
                Pronosticar
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Grupos */}
      <div>
        <p className="label mb-3">Grupos</p>
        <div className="grid lg:grid-cols-2 gap-3">
          {GRUPOS.map(grupo => (
            <div key={grupo.letra} className="card">
              <div className="px-4 py-3 border-b border-border">
                <p className="text-sm font-semibold text-content-primary">Grupo {grupo.letra}</p>
              </div>
              <div className="divide-y divide-border">
                {grupo.equipos.map((eq, i) => {
                  const Flag = Flags[eq.codigo]
                  return (
                    <div key={eq.pais} className="px-4 py-2.5 flex items-center gap-3">
                      <span className="text-xs text-content-muted w-4 shrink-0">{i + 1}</span>
                      {Flag && <Flag className="w-5 rounded-sm shrink-0" />}
                      <span className="flex-1 text-sm text-content-primary">{eq.pais}</span>
                      <div className="flex gap-3 text-xs font-medium">
                        <span className="text-content-primary w-4 text-right" title="Puntos">{eq.pts}</span>
                        <span className="text-content-muted w-4 text-right" title="PJ">{eq.pj}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function TeamDisplay({ codigo, nombre }: { codigo: keyof typeof Flags; nombre: string }) {
  const Flag = Flags[codigo]
  return (
    <div className="text-center flex-1">
      <div className="flex justify-center mb-2">
        {Flag && <Flag className="w-10 rounded" />}
      </div>
      <p className="text-sm font-semibold text-content-primary">{nombre}</p>
    </div>
  )
}

function PlaceholderContent({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3 animate-fade-in">
      <div className="w-12 h-12 rounded-xl bg-bg-surface border border-border flex items-center justify-center">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="8" stroke="#2A2A2A" strokeWidth="1.5" />
          <path d="M10 6v4M10 12v.5" stroke="#4A4A4A" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <h2 className="text-base font-semibold text-content-primary">{title}</h2>
      <p className="text-xs text-content-muted">Próximamente</p>
    </div>
  )
}

// ── Icons ──────────────────────────────────────────────────────────────────

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
