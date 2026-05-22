import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

interface ProdeUser {
  id: string
  email: string
  nombre: string
  apellido: string
  activo: boolean
  is_admin: boolean
  must_change_password: boolean
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

  const token = localStorage.getItem('prode_token')

  const authHeaders = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/prode/admin/users', { headers: authHeaders })
      if (res.status === 403) { navigate('/dashboard'); return }
      setUsers(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])  // eslint-disable-line

  useEffect(() => { fetchUsers() }, [fetchUsers])

  async function createUser() {
    setActionLoading(true)
    try {
      const res = await fetch('/api/prode/admin/users', {
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
      const res = await fetch(`/api/prode/admin/users/${selected.id}`, {
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
      await fetch(`/api/prode/admin/users/${user.id}`, {
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

  async function deleteUser() {
    if (!selected) return
    setActionLoading(true)
    try {
      await fetch(`/api/prode/admin/users/${selected.id}`, { method: 'DELETE', headers: authHeaders })
      setModal(null)
      await fetchUsers()
      showToast('Usuario eliminado')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="min-h-dvh bg-bg-base font-mori animate-fade-in">
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
          <button
            onClick={() => setModal('create')}
            className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
          >
            <IconPlus /> Nuevo usuario
          </button>
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
                      {user.is_admin
                        ? <span className="text-xs font-semibold text-accent bg-accent-subtle border border-accent-border px-2 py-0.5 rounded-full">Admin</span>
                        : <span className="text-xs text-content-muted">Jugador</span>
                      }
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

function IconBack() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
}
function IconPlus() {
  return <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M7.5 2v11M2 7.5h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
}
function IconX() {
  return <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></svg>
}
