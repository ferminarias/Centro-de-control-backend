import { API } from '../lib/api'
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

interface ProdeUser {
  id: string
  email: string
  nombre: string
  apellido: string
  activo: boolean
  is_admin: boolean
  es_gerente: boolean
  must_change_password: boolean
  created_at: string
}

interface PartidoSimple {
  id: number
  equipo_local: { nombre: string } | null
  equipo_visitante: { nombre: string } | null
  fecha: string
  estado: string
}

interface Invitacion {
  token: string
  creado_por: string
  created_at: string
  activo: boolean
}

interface RegistroPendiente {
  id: string
  email: string
  nombre: string
  apellido: string
  estado: string
  created_at: string
}

const DEFAULT_PASSWORD = 'Nodsprode'

export default function Admin() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<ProdeUser[]>([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState<'create' | 'reset' | 'delete' | null>(null)
  const [selected, setSelected] = useState<ProdeUser | null>(null)
  const [form, setForm] = useState({ nombre: '', apellido: '', email: '', is_admin: false })
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [partidos, setPartidos] = useState<PartidoSimple[]>([])
  const [simPartidoId, setSimPartidoId] = useState<number | ''>('')
  const [simGl, setSimGl] = useState(1)
  const [simGv, setSimGv] = useState(0)
  const [simLoading, setSimLoading] = useState(false)

  const [invitaciones, setInvitaciones] = useState<Invitacion[]>([])
  const [invLoading, setInvLoading] = useState(false)
  const [copiedToken, setCopiedToken] = useState<string | null>(null)

  const [pendientes, setPendientes] = useState<RegistroPendiente[]>([])
  const [pendientesLoading, setPendientesLoading] = useState(false)

  const [resetLoading, setResetLoading] = useState(false)
  const [equiposAll, setEquiposAll] = useState<{ id: number; nombre: string; codigo_iso: string }[]>([])
  const [ganadorId, setGanadorId] = useState<number | ''>('')
  const [ganadorLoading, setGanadorLoading] = useState(false)

  const token = localStorage.getItem('prode_token')

  const authHeaders = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(API + '/api/prode/admin/users', { headers: authHeaders })
      if (res.status === 403) { navigate('/dashboard'); return }
      setUsers(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])  // eslint-disable-line

  useEffect(() => { fetchUsers() }, [fetchUsers])

  useEffect(() => {
    fetch(API + '/api/prode/partidos', { headers: authHeaders })
      .then(r => r.json())
      .then((data: PartidoSimple[]) => setPartidos(Array.isArray(data) ? data : []))
      .catch(() => {})
  }, []) // eslint-disable-line

  const fetchInvitaciones = useCallback(async () => {
    try {
      const res = await fetch(API + '/api/prode/admin/invitaciones', { headers: authHeaders })
      if (res.ok) setInvitaciones(await res.json())
    } catch {}
  }, []) // eslint-disable-line

  const fetchPendientes = useCallback(async () => {
    try {
      const res = await fetch(API + '/api/prode/admin/pendientes', { headers: authHeaders })
      if (res.ok) setPendientes(await res.json())
    } catch {}
  }, []) // eslint-disable-line

  useEffect(() => {
    fetchInvitaciones()
    fetchPendientes()
  }, [fetchInvitaciones, fetchPendientes])

  async function generarInvitacion() {
    setInvLoading(true)
    try {
      const res = await fetch(API + '/api/prode/admin/invitaciones', { method: 'POST', headers: authHeaders })
      if (!res.ok) throw new Error()
      await fetchInvitaciones()
      showToast('Link de invitación generado')
    } catch {
      showToast('Error al generar invitación')
    } finally {
      setInvLoading(false)
    }
  }

  async function revocarInvitacion(token: string) {
    try {
      await fetch(API + `/api/prode/admin/invitaciones/${token}`, { method: 'DELETE', headers: authHeaders })
      await fetchInvitaciones()
      showToast('Link revocado')
    } catch {
      showToast('Error al revocar')
    }
  }

  function copiarLink(token: string) {
    const url = `${window.location.origin}/registro/${token}`
    navigator.clipboard.writeText(url).then(() => {
      setCopiedToken(token)
      setTimeout(() => setCopiedToken(null), 2000)
    })
  }

  async function aceptarRegistro(id: string) {
    setPendientesLoading(true)
    try {
      const res = await fetch(API + `/api/prode/admin/pendientes/${id}/aceptar`, { method: 'POST', headers: authHeaders })
      if (!res.ok) {
        const d = await res.json()
        showToast(d.detail || 'Error al aceptar')
        return
      }
      await fetchPendientes()
      await fetchUsers()
      showToast('Usuario aceptado y cuenta creada')
    } catch {
      showToast('Error al aceptar')
    } finally {
      setPendientesLoading(false)
    }
  }

  async function rechazarRegistro(id: string) {
    setPendientesLoading(true)
    try {
      await fetch(API + `/api/prode/admin/pendientes/${id}/rechazar`, { method: 'POST', headers: authHeaders })
      await fetchPendientes()
      showToast('Solicitud rechazada')
    } catch {
      showToast('Error al rechazar')
    } finally {
      setPendientesLoading(false)
    }
  }

  async function simularPartido() {
    if (!simPartidoId) return
    setSimLoading(true)
    try {
      const res = await fetch(API + `/api/prode/admin/partidos/${simPartidoId}/simular`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ goles_local: simGl, goles_visitante: simGv }),
      })
      if (!res.ok) throw new Error('Error al simular')
      showToast(`Partido simulado en vivo: ${simGl}-${simGv}`)
    } catch {
      showToast('Error al simular partido')
    } finally {
      setSimLoading(false)
    }
  }

  async function finalizarPartido() {
    if (!simPartidoId) return
    setSimLoading(true)
    try {
      const res = await fetch(API + `/api/prode/admin/partidos/${simPartidoId}/finalizar`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ goles_local: simGl, goles_visitante: simGv }),
      })
      if (!res.ok) throw new Error('Error al finalizar')
      const data = await res.json()
      showToast(`Partido finalizado · ${data.predicciones_puntuadas} predicciones puntuadas`)
    } catch {
      showToast('Error al finalizar partido')
    } finally {
      setSimLoading(false)
    }
  }

  async function resetearPartido() {
    if (!simPartidoId) return
    setSimLoading(true)
    try {
      await fetch(API + `/api/prode/admin/partidos/${simPartidoId}/resetear`, {
        method: 'PATCH',
        headers: authHeaders,
      })
      showToast('Partido reseteado a programado')
    } catch {
      showToast('Error al resetear')
    } finally {
      setSimLoading(false)
    }
  }

  async function createUser() {
    setActionLoading(true)
    try {
      const res = await fetch(API + '/api/prode/admin/users', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ ...form, password: DEFAULT_PASSWORD }),
      })
      if (!res.ok) {
        const d = await res.json()
        throw new Error(d.detail || 'Error al crear usuario')
      }
      setModal(null)
      setForm({ nombre: '', apellido: '', email: '', is_admin: false })
      await fetchUsers()
      showToast(`Usuario creado · contraseña inicial: ${DEFAULT_PASSWORD}`)
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Error')
    } finally {
      setActionLoading(false)
    }
  }

  async function resetPassword() {
    if (!selected) return
    setActionLoading(true)
    try {
      const res = await fetch(API + `/api/prode/admin/users/${selected.id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ new_password: DEFAULT_PASSWORD }),
      })
      if (!res.ok) throw new Error('Error al resetear contraseña')
      setModal(null)
      await fetchUsers()
      showToast(`Contraseña reseteada a: ${DEFAULT_PASSWORD}`)
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Error')
    } finally {
      setActionLoading(false)
    }
  }

  async function toggleActive(user: ProdeUser) {
    try {
      await fetch(API + `/api/prode/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ activo: !user.activo }),
      })
      await fetchUsers()
      showToast(user.activo ? 'Usuario desactivado' : 'Usuario activado')
    } catch {
      showToast('Error al actualizar usuario')
    }
  }

  async function toggleAdmin(user: ProdeUser) {
    try {
      await fetch(API + `/api/prode/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ is_admin: !user.is_admin }),
      })
      await fetchUsers()
      showToast(user.is_admin ? 'Rol cambiado a Jugador' : 'Rol cambiado a Admin')
    } catch {
      showToast('Error al actualizar usuario')
    }
  }

  async function toggleGerente(user: ProdeUser) {
    try {
      await fetch(API + `/api/prode/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ es_gerente: !user.es_gerente }),
      })
      await fetchUsers()
      showToast(user.es_gerente ? 'Rol líder quitado' : 'Rol líder asignado — ya puede crear equipos')
    } catch {
      showToast('Error al actualizar usuario')
    }
  }

  async function syncFixtures() {
    setSyncing(true)
    try {
      const res = await fetch(API + '/api/prode/admin/sync', { method: 'POST', headers: authHeaders })
      if (!res.ok) {
        const d = await res.json()
        showToast(d.detail || 'Error al sincronizar')
        return
      }
      const d = await res.json()
      showToast(`Sync OK · ${d.partidos_creados} nuevos · ${d.partidos_actualizados} actualizados · ${d.predicciones_puntuadas} pts calculados`)
    } catch {
      showToast('Error al conectar con el servidor')
    } finally {
      setSyncing(false)
    }
  }

  async function deleteUser() {
    if (!selected) return
    setActionLoading(true)
    try {
      await fetch(API + `/api/prode/admin/users/${selected.id}`, { method: 'DELETE', headers: authHeaders })
      setModal(null)
      await fetchUsers()
      showToast('Usuario desactivado (historial de pronósticos preservado)')
    } finally {
      setActionLoading(false)
    }
  }

  useEffect(() => {
    fetch(API + '/api/prode/apuesta-ganador/equipos', { headers: authHeaders })
      .then(r => r.json()).then(setEquiposAll).catch(() => {})
  }, []) // eslint-disable-line

  async function resetPuntos() {
    if (!confirm('¿Resetear TODOS los puntos? Esto borrará los puntos de todas las predicciones y la apuesta ganador. Esta acción no se puede deshacer.')) return
    setResetLoading(true)
    try {
      const res = await fetch(API + '/api/prode/admin/reset-puntos', { method: 'POST', headers: authHeaders })
      const d = await res.json()
      showToast(`Puntos reseteados · ${d.predicciones_reseteadas} predicciones · ${d.apuestas_reseteadas} apuestas`)
    } catch {
      showToast('Error al resetear')
    } finally {
      setResetLoading(false)
    }
  }

  async function declararGanador() {
    if (!ganadorId) return
    const equipo = equiposAll.find(e => e.id === ganadorId)
    if (!confirm(`¿Declarar a ${equipo?.nombre} como campeón del mundial? Se otorgarán 25 pts a quienes apostaron por este equipo.`)) return
    setGanadorLoading(true)
    try {
      const res = await fetch(API + '/api/prode/admin/apuesta-ganador/resultado', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ equipo_id: ganadorId }),
      })
      const d = await res.json()
      showToast(`Campeón declarado: ${d.ganador} · ${d.acertaron} usuarios acertaron`)
    } catch {
      showToast('Error al declarar ganador')
    } finally {
      setGanadorLoading(false)
    }
  }

  return (
    <div className="min-h-dvh font-mori animate-fade-in">
      {/* Header */}
      <header className="h-14 border-b border-border bg-bg-base flex items-center px-6 gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-content-secondary hover:text-content-primary transition-colors text-sm"
        >
          <IconBack /> Dashboard
        </button>
        <div className="flex-1" />
        <div className="overflow-hidden" style={{ height: '22px' }}>
          <img src="/logo-nods.png" alt="NODS" style={{ height: '35px', width: 'auto' }} />
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-6">
        {/* Title row */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold text-content-primary">Usuarios</h1>
            <p className="text-sm text-content-secondary mt-0.5">{users.length} participantes registrados</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={syncFixtures}
              disabled={syncing}
              className="flex items-center gap-2 bg-bg-surface hover:bg-bg-elevated text-content-secondary text-sm font-semibold px-4 py-2.5 rounded-lg border border-border transition-colors disabled:opacity-50"
            >
              <IconSync spinning={syncing} /> {syncing ? 'Sincronizando...' : 'Sync fixture'}
            </button>
            <button
              onClick={() => setModal('create')}
              className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
            >
              <IconPlus /> Nuevo usuario
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : users.length === 0 ? (
            <div className="py-16 text-center text-content-muted text-sm">No hay usuarios todavía</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="label text-left px-4 py-3">Nombre</th>
                  <th className="label text-left px-4 py-3">Email</th>
                  <th className="label text-left px-4 py-3">Estado</th>
                  <th className="label text-left px-4 py-3">Rol</th>
                  <th className="label text-left px-4 py-3">Contraseña</th>
                  <th className="label text-left px-4 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-bg-elevated transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-full bg-bg-elevated border border-border flex items-center justify-center text-[11px] font-semibold text-content-secondary shrink-0">
                          {user.nombre[0]}{user.apellido[0]}
                        </div>
                        <span className="text-content-primary font-medium">{user.nombre} {user.apellido}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-content-secondary">{user.email}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleActive(user)}
                        className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full transition-colors ${
                          user.activo
                            ? 'bg-status-win/10 text-status-win hover:bg-status-win/20'
                            : 'bg-border text-content-muted hover:bg-border-strong'
                        }`}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${user.activo ? 'bg-status-win' : 'bg-content-muted'}`} />
                        {user.activo ? 'Activo' : 'Inactivo'}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => toggleAdmin(user)}
                          className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full transition-colors ${
                            user.is_admin
                              ? 'bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20'
                              : 'bg-border text-content-muted border border-transparent hover:bg-border-strong'
                          }`}
                          title={user.is_admin ? 'Quitar admin' : 'Dar admin'}
                        >
                          {user.is_admin ? 'Admin' : 'Jugador'}
                        </button>
                        <button
                          onClick={() => toggleGerente(user)}
                          className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full transition-colors ${
                            user.es_gerente
                              ? 'bg-status-draw/10 text-status-draw border border-status-draw/20 hover:bg-status-draw/20'
                              : 'bg-border text-content-muted border border-transparent hover:bg-border-strong'
                          }`}
                          title={user.es_gerente ? 'Quitar rol líder' : 'Dar rol líder (puede crear equipos)'}
                        >
                          {user.es_gerente ? 'Líder ✓' : 'Líder'}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {user.must_change_password
                        ? <span className="text-xs text-status-draw">Pendiente cambio</span>
                        : <span className="text-xs text-content-muted">Personalizada</span>
                      }
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => { setSelected(user); setModal('reset') }}
                          className="text-xs text-content-secondary hover:text-content-primary border border-border hover:border-border-strong px-2.5 py-1 rounded-lg transition-all"
                          title="Resetear contraseña"
                        >
                          Reset pwd
                        </button>
                        <button
                          onClick={() => { setSelected(user); setModal('delete') }}
                          className="text-xs text-content-muted hover:text-status-loss border border-border hover:border-red-500/30 px-2.5 py-1 rounded-lg transition-all"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Invitaciones */}
        <div className="mt-8">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-content-primary">Links de invitación</h2>
              <p className="text-xs text-content-muted mt-0.5">Cualquiera con el link puede solicitar acceso</p>
            </div>
            <button
              onClick={generarInvitacion}
              disabled={invLoading}
              className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white text-sm font-semibold px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              <IconPlus /> Generar link
            </button>
          </div>
          <div className="card overflow-hidden">
            {invitaciones.filter(i => i.activo).length === 0 ? (
              <div className="py-10 text-center text-content-muted text-sm">No hay links activos</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="label text-left px-4 py-3">Link</th>
                    <th className="label text-left px-4 py-3">Creado</th>
                    <th className="label text-left px-4 py-3">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {invitaciones.filter(i => i.activo).map(inv => (
                    <tr key={inv.token} className="hover:bg-bg-elevated transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs text-content-secondary bg-bg-elevated border border-border rounded px-2 py-1 select-all">
                          {`${window.location.origin}/registro/${inv.token}`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-content-muted text-xs">
                        {new Date(inv.created_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copiarLink(inv.token)}
                            className="text-xs text-content-secondary hover:text-accent border border-border hover:border-accent/30 px-2.5 py-1 rounded-lg transition-all"
                          >
                            {copiedToken === inv.token ? '¡Copiado!' : 'Copiar link'}
                          </button>
                          <button
                            onClick={() => revocarInvitacion(inv.token)}
                            className="text-xs text-content-muted hover:text-status-loss border border-border hover:border-red-500/30 px-2.5 py-1 rounded-lg transition-all"
                          >
                            Revocar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Solicitudes pendientes */}
        {pendientes.length > 0 && (
          <div className="mt-8">
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-sm font-semibold text-content-primary">Solicitudes pendientes</h2>
              <span className="text-xs font-bold bg-accent/20 text-accent border border-accent/30 px-2 py-0.5 rounded-full">
                {pendientes.length}
              </span>
            </div>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="label text-left px-4 py-3">Nombre</th>
                    <th className="label text-left px-4 py-3">Email</th>
                    <th className="label text-left px-4 py-3">Fecha</th>
                    <th className="label text-left px-4 py-3">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {pendientes.map(reg => (
                    <tr key={reg.id} className="hover:bg-bg-elevated transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-7 h-7 rounded-full bg-bg-elevated border border-border flex items-center justify-center text-[11px] font-semibold text-content-secondary shrink-0">
                            {reg.nombre[0]}{reg.apellido[0]}
                          </div>
                          <span className="text-content-primary font-medium">{reg.nombre} {reg.apellido}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-content-secondary">{reg.email}</td>
                      <td className="px-4 py-3 text-content-muted text-xs">
                        {new Date(reg.created_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short' })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => aceptarRegistro(reg.id)}
                            disabled={pendientesLoading}
                            className="text-xs font-semibold text-status-win hover:bg-status-win/10 border border-status-win/30 px-2.5 py-1 rounded-lg transition-all disabled:opacity-50"
                          >
                            Aceptar
                          </button>
                          <button
                            onClick={() => rechazarRegistro(reg.id)}
                            disabled={pendientesLoading}
                            className="text-xs text-content-muted hover:text-status-loss border border-border hover:border-red-500/30 px-2.5 py-1 rounded-lg transition-all disabled:opacity-50"
                          >
                            Rechazar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Simulador */}
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[10px] font-bold text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full uppercase tracking-wider">Solo pruebas</span>
            <h2 className="text-sm font-semibold text-content-primary">Simulador de partido en vivo</h2>
          </div>
          <div className="card p-5 flex flex-col gap-4">
            <p className="text-xs text-content-muted"><span className="text-emerald-400 font-medium">En vivo</span> — simula el partido en curso. <span className="text-blue-400 font-medium">Finalizar y puntuar</span> — cierra el partido y calcula los puntos de cada predicción. <span className="text-content-secondary font-medium">Resetear</span> — vuelve a programado.</p>

            {/* Selector de partido */}
            <div className="flex flex-col gap-1.5">
              <label className="label">Partido</label>
              <select
                value={simPartidoId}
                onChange={e => setSimPartidoId(e.target.value ? Number(e.target.value) : '')}
                className="input-field"
              >
                <option value="">Seleccioná un partido...</option>
                {partidos.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.equipo_local?.nombre ?? '?'} vs {p.equipo_visitante?.nombre ?? '?'}
                    {p.estado === 'en_juego' ? ' 🟢 (en vivo)' : p.estado === 'finalizado' ? ' (finalizado)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Marcador */}
            <div className="flex items-end gap-3">
              <div className="flex flex-col gap-1.5 flex-1">
                <label className="label">Goles local</label>
                <input
                  type="number" min={0} max={20}
                  value={simGl}
                  onChange={e => setSimGl(Math.max(0, Number(e.target.value)))}
                  className="input-field text-center text-lg font-semibold"
                />
              </div>
              <span className="text-xl text-content-muted font-light pb-2.5">—</span>
              <div className="flex flex-col gap-1.5 flex-1">
                <label className="label">Goles visitante</label>
                <input
                  type="number" min={0} max={20}
                  value={simGv}
                  onChange={e => setSimGv(Math.max(0, Number(e.target.value)))}
                  className="input-field text-center text-lg font-semibold"
                />
              </div>
              <div className="flex gap-2 pb-0.5 flex-wrap">
                <button
                  onClick={simularPartido}
                  disabled={simLoading || !simPartidoId}
                  className="flex items-center gap-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors disabled:opacity-40"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  {simLoading ? 'Cargando...' : 'En vivo'}
                </button>
                <button
                  onClick={finalizarPartido}
                  disabled={simLoading || !simPartidoId}
                  className="flex items-center gap-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 text-blue-400 text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors disabled:opacity-40"
                >
                  ✓ Finalizar y puntuar
                </button>
                <button
                  onClick={resetearPartido}
                  disabled={simLoading || !simPartidoId}
                  className="text-sm font-semibold px-4 py-2.5 rounded-lg border border-border text-content-muted hover:text-content-primary hover:border-border-strong transition-colors disabled:opacity-40"
                >
                  Resetear
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Apuesta Campeón — declarar ganador */}
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base">🏆</span>
            <h2 className="text-sm font-semibold text-content-primary">Campeón del Mundial</h2>
          </div>
          <div className="card p-5 flex flex-col gap-4">
            <p className="text-xs text-content-muted">Al declarar el campeón se otorgan automáticamente <span className="text-content-primary font-semibold">25 puntos</span> a todos los usuarios que apostaron por ese equipo. Se puede ejecutar más de una vez si hubo error.</p>
            <div className="flex gap-2">
              <select
                value={ganadorId}
                onChange={e => setGanadorId(e.target.value ? Number(e.target.value) : '')}
                className="input-field flex-1 py-2"
              >
                <option value="">Seleccioná el campeón...</option>
                {equiposAll.map(eq => (
                  <option key={eq.id} value={eq.id}>{eq.nombre}</option>
                ))}
              </select>
              <button
                onClick={declararGanador}
                disabled={ganadorLoading || !ganadorId}
                className="bg-accent hover:bg-accent-hover text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors disabled:opacity-40 shrink-0"
              >
                {ganadorLoading ? 'Procesando...' : 'Declarar campeón'}
              </button>
            </div>
          </div>
        </div>

        {/* Reset de puntos */}
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[10px] font-bold text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-0.5 rounded-full uppercase tracking-wider">Peligroso</span>
            <h2 className="text-sm font-semibold text-content-primary">Resetear todos los puntos</h2>
          </div>
          <div className="card p-5">
            <p className="text-xs text-content-muted mb-4">Pone en <span className="text-content-primary font-medium">null</span> los puntos de todas las predicciones y resetea a 0 los puntos de la apuesta ganador. Usalo solo si hubo un error en el cálculo. Las predicciones en sí <span className="text-content-primary font-medium">no se eliminan</span>.</p>
            <button
              onClick={resetPuntos}
              disabled={resetLoading}
              className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors disabled:opacity-40"
            >
              {resetLoading ? 'Reseteando...' : 'Resetear todos los puntos'}
            </button>
          </div>
        </div>
      </main>

      {/* Modal crear usuario */}
      {modal === 'create' && (
        <Modal title="Nuevo usuario" onClose={() => setModal(null)}>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="label">Nombre</label>
                <input className="input-field" placeholder="Juan" value={form.nombre} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} autoFocus />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="label">Apellido</label>
                <input className="input-field" placeholder="Pérez" value={form.apellido} onChange={e => setForm(f => ({ ...f, apellido: e.target.value }))} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="label">Email</label>
              <input className="input-field" type="email" placeholder="juan@gruponods.com" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
            </div>
            <label className="flex items-center gap-2.5 cursor-pointer">
              <div
                onClick={() => setForm(f => ({ ...f, is_admin: !f.is_admin }))}
                className={`w-9 h-5 rounded-full transition-colors flex items-center px-0.5 ${form.is_admin ? 'bg-accent' : 'bg-border-strong'}`}
              >
                <div className={`w-4 h-4 bg-white rounded-full shadow transition-transform ${form.is_admin ? 'translate-x-4' : 'translate-x-0'}`} />
              </div>
              <span className="text-sm text-content-secondary">Rol administrador</span>
            </label>
            <div className="bg-bg-elevated border border-border rounded-lg px-3 py-2.5 text-xs text-content-secondary">
              Contraseña inicial: <span className="font-semibold text-content-primary font-mono">{DEFAULT_PASSWORD}</span> · El usuario deberá cambiarla al ingresar
            </div>
          </div>
          <div className="flex gap-2 mt-6">
            <button onClick={() => setModal(null)} className="btn-ghost flex-1">Cancelar</button>
            <button
              onClick={createUser}
              disabled={actionLoading || !form.nombre || !form.apellido || !form.email}
              className="flex-1 bg-accent hover:bg-accent-hover text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading ? 'Creando...' : 'Crear usuario'}
            </button>
          </div>
        </Modal>
      )}

      {/* Modal resetear contraseña */}
      {modal === 'reset' && selected && (
        <Modal title="Resetear contraseña" onClose={() => setModal(null)}>
          <p className="text-sm text-content-secondary mb-2">
            Se va a resetear la contraseña de <span className="font-semibold text-content-primary">{selected.nombre} {selected.apellido}</span>.
          </p>
          <div className="bg-bg-elevated border border-border rounded-lg px-3 py-2.5 text-xs text-content-secondary">
            Nueva contraseña: <span className="font-semibold text-content-primary font-mono">{DEFAULT_PASSWORD}</span> · El usuario deberá cambiarla al ingresar
          </div>
          <div className="flex gap-2 mt-6">
            <button onClick={() => setModal(null)} className="btn-ghost flex-1">Cancelar</button>
            <button onClick={resetPassword} disabled={actionLoading} className="flex-1 bg-accent hover:bg-accent-hover text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50">
              {actionLoading ? 'Reseteando...' : 'Confirmar reset'}
            </button>
          </div>
        </Modal>
      )}

      {/* Modal eliminar */}
      {modal === 'delete' && selected && (
        <Modal title="Eliminar usuario" onClose={() => setModal(null)}>
          <p className="text-sm text-content-secondary">
            ¿Estás seguro que querés eliminar a <span className="font-semibold text-content-primary">{selected.nombre} {selected.apellido}</span>? Esta acción no se puede deshacer.
          </p>
          <div className="flex gap-2 mt-6">
            <button onClick={() => setModal(null)} className="btn-ghost flex-1">Cancelar</button>
            <button onClick={deleteUser} disabled={actionLoading} className="flex-1 bg-red-500/90 hover:bg-red-500 text-white font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50">
              {actionLoading ? 'Eliminando...' : 'Eliminar'}
            </button>
          </div>
        </Modal>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-bg-elevated border border-border rounded-xl px-5 py-3 text-sm text-content-primary shadow-card-hover animate-slide-up z-50">
          {toast}
        </div>
      )}
    </div>
  )
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-40 p-4 animate-fade-in">
      <div className="card w-full max-w-md p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-content-primary">{title}</h2>
          <button onClick={onClose} className="text-content-muted hover:text-content-primary transition-colors">
            <IconX />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function IconSync({ spinning }: { spinning: boolean }) {
  return (
    <svg
      width="15" height="15" viewBox="0 0 15 15" fill="none"
      className={spinning ? 'animate-spin' : ''}
    >
      <path d="M13.5 7.5A6 6 0 112.5 4M2.5 1v3h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
function IconBack() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
function IconPlus() {
  return <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M7.5 2v11M2 7.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
}
function IconX() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
