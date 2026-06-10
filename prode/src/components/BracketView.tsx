import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import * as Flags from 'country-flag-icons/react/3x2'

// ── Types ─────────────────────────────────────────────────────────────────────
// Structural subset of Dashboard's Partido — anything with these fields works.

export interface BracketEquipo {
  nombre: string
  codigo_iso: string
}

export interface BracketPartido {
  id: number
  equipo_local: BracketEquipo | null
  equipo_visitante: BracketEquipo | null
  fecha: string
  fase: string
  goles_local: number | null
  goles_visitante: number | null
  estado: string
}

interface Props {
  partidos: BracketPartido[]
  tz?: string
}

// ── Geometry ──────────────────────────────────────────────────────────────────

const CARD_W = 172
const CARD_H = 80
const ROW_GAP = 12
const COL_GAP = 44
const PAD_X = 24
const PAD_TOP = 48
const STEP = CARD_H + ROW_GAP

const COL_LABELS = [
  'Ronda de 32', 'Octavos', 'Cuartos', 'Semifinal',
  'Final',
  'Semifinal', 'Cuartos', 'Octavos', 'Ronda de 32',
]

const colX = (c: number) => PAD_X + c * (CARD_W + COL_GAP)
const TOTAL_W = colX(8) + CARD_W + PAD_X
const TOTAL_H = PAD_TOP + 8 * CARD_H + 7 * ROW_GAP + 24

// ── Helpers ───────────────────────────────────────────────────────────────────

function Flag({ codigo, className }: { codigo: string; className?: string }) {
  const FlagComp = (Flags as Record<string, React.ComponentType<{ className?: string }>>)[codigo]
  if (!FlagComp) return <span className={`inline-block bg-border rounded-sm ${className ?? 'w-5'}`} />
  return <FlagComp className={className ?? 'w-5 rounded-sm'} />
}

type Lado = 'local' | 'visitante'

function ganador(p: BracketPartido | null): Lado | null {
  if (!p || p.estado !== 'finalizado') return null
  const gl = p.goles_local ?? 0
  const gv = p.goles_visitante ?? 0
  if (gl > gv) return 'local'
  if (gv > gl) return 'visitante'
  return null // empate en 90' — penales no modelados en la API
}

// Approximate match minute from kick-off time (same heuristic as Dashboard)
function minuteLabel(fecha: string): string {
  const elapsed = (Date.now() - new Date(fecha).getTime()) / 60000
  if (elapsed < 0) return 'LIVE'
  if (elapsed <= 45) return `${Math.min(45, Math.floor(elapsed))}'`
  if (elapsed <= 60) return 'HT'
  const min2 = Math.floor(elapsed - 15)
  if (min2 <= 90) return `${Math.min(90, min2)}'`
  return '90+'
}

function useLiveMinute(fecha: string, estado: string): string {
  const [, bump] = useState(0)
  useEffect(() => {
    if (estado !== 'en_juego') return
    const t = setInterval(() => bump(n => n + 1), 30_000)
    return () => clearInterval(t)
  }, [estado])
  return estado === 'en_juego' ? minuteLabel(fecha) : ''
}

// ── Layout model ──────────────────────────────────────────────────────────────

interface BNode {
  key: string
  col: number
  x: number
  y: number
  partido: BracketPartido | null
}

interface BLink {
  from: BNode
  to: BNode
  dir: 1 | -1 // 1 = hacia la derecha (lado izquierdo), -1 = hacia la izquierda
  active: boolean
}

function buildLayout(partidos: BracketPartido[]) {
  const sorted = (...fases: string[]) =>
    partidos
      .filter(p => fases.includes(p.fase))
      .sort((a, b) => new Date(a.fecha).getTime() - new Date(b.fecha).getTime() || a.id - b.id)

  // Sin número FIFA en la API: el orden cronológico dentro de cada fase es el
  // mejor proxy de la numeración oficial (M73–M104 se juegan en orden).
  const r32 = sorted('r32')
  const r16 = sorted('r16')
  const qf = sorted('cuartos')
  const sf = sorted('semis', 'semifinal')
  const fin = sorted('final')[0] ?? null
  const ter = sorted('tercero', 'tercer_puesto')[0] ?? null

  const ys32 = Array.from({ length: 8 }, (_, i) => PAD_TOP + i * STEP)
  const pair = (ys: number[]) => Array.from({ length: ys.length / 2 }, (_, i) => (ys[2 * i] + ys[2 * i + 1]) / 2)
  const ys16 = pair(ys32)
  const ysQF = pair(ys16)
  const ysSF = pair(ysQF)
  const yFinal = ysSF[0]

  const slot = <T,>(arr: T[], i: number): T | null => arr[i] ?? null

  const mk = (key: string, col: number, y: number, p: BracketPartido | null): BNode =>
    ({ key, col, x: colX(col), y, partido: p })

  // Lado izquierdo: primera mitad de cada fase. Derecho: segunda mitad.
  const cols: BNode[][] = [
    ys32.map((y, i) => mk(`L32-${i}`, 0, y, slot(r32, i))),
    ys16.map((y, i) => mk(`L16-${i}`, 1, y, slot(r16, i))),
    ysQF.map((y, i) => mk(`LQF-${i}`, 2, y, slot(qf, i))),
    [mk('LSF', 3, ysSF[0], slot(sf, 0))],
    [mk('FIN', 4, yFinal, fin)],
    [mk('RSF', 5, ysSF[0], slot(sf, 1))],
    ysQF.map((y, i) => mk(`RQF-${i}`, 6, y, slot(qf, 2 + i))),
    ys16.map((y, i) => mk(`R16-${i}`, 7, y, slot(r16, 4 + i))),
    ys32.map((y, i) => mk(`R32-${i}`, 8, y, slot(r32, 8 + i))),
  ]

  const links: BLink[] = []
  const connect = (children: BNode[], parents: BNode[], dir: 1 | -1) => {
    children.forEach((child, i) => {
      const parent = parents[i >> 1]
      if (parent) links.push({ from: child, to: parent, dir, active: ganador(child.partido) !== null })
    })
  }
  connect(cols[0], cols[1], 1)
  connect(cols[1], cols[2], 1)
  connect(cols[2], cols[3], 1)
  connect(cols[3], cols[4], 1)
  connect(cols[8], cols[7], -1)
  connect(cols[7], cols[6], -1)
  connect(cols[6], cols[5], -1)
  connect(cols[5], cols[4], -1)

  const tercero: BNode = mk('TER', 4, yFinal + CARD_H + 44, ter)
  const nodes = [...cols.flat(), tercero]
  const finalNode = cols[4][0]

  return { nodes, links, finalNode, tercero, yFinal }
}

// Elbow path with rounded corners between a child card and its parent slot
function linkPath(l: BLink): string {
  const y1 = l.from.y + CARD_H / 2
  const y2 = l.to.y + CARD_H / 2
  const x1 = l.dir === 1 ? l.from.x + CARD_W : l.from.x
  const x2 = l.dir === 1 ? l.to.x : l.to.x + CARD_W
  const midX = x1 + (l.dir * COL_GAP) / 2
  if (Math.abs(y1 - y2) < 1) return `M ${x1} ${y1} L ${x2} ${y2}`
  const s = y2 > y1 ? 1 : -1
  const r = Math.min(10, Math.abs(y2 - y1) / 2)
  return [
    `M ${x1} ${y1}`,
    `L ${midX - l.dir * r} ${y1}`,
    `Q ${midX} ${y1} ${midX} ${y1 + s * r}`,
    `L ${midX} ${y2 - s * r}`,
    `Q ${midX} ${y2} ${midX + l.dir * r} ${y2}`,
    `L ${x2} ${y2}`,
  ].join(' ')
}

// ── Match card ────────────────────────────────────────────────────────────────

function fechaCorta(iso: string, tz?: string) {
  const d = new Date(iso)
  const date = d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', timeZone: tz })
  const time = d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', timeZone: tz })
  return `${date} · ${time}`
}

function TeamLine({ equipo, goles, esGanador, esPerdedor, live }: {
  equipo: BracketEquipo | null
  goles: number | null
  esGanador: boolean
  esPerdedor: boolean
  live: boolean
}) {
  if (!equipo) {
    return (
      <div className="flex items-center gap-2 h-6">
        <span className="w-5 h-[14px] rounded-sm border border-dashed border-border-strong shrink-0" />
        <span className="text-[11px] text-content-muted truncate">Por definir</span>
      </div>
    )
  }
  return (
    <div className={`flex items-center gap-2 h-6 transition-opacity ${esPerdedor ? 'opacity-40' : ''}`}>
      <Flag codigo={equipo.codigo_iso} className="w-5 rounded-sm shrink-0" />
      <span className={`text-[11px] truncate flex-1 ${esGanador ? 'text-content-primary font-semibold' : 'text-content-secondary font-medium'}`}>
        {equipo.nombre}
      </span>
      <span className={`text-xs tabular-nums shrink-0 ${
        live ? 'text-amber-400 font-bold' : esGanador ? 'text-content-primary font-bold' : 'text-content-secondary font-semibold'
      }`}>
        {goles ?? '—'}
      </span>
    </div>
  )
}

function MatchCard({ node, tz, destacado }: { node: BNode; tz?: string; destacado?: boolean }) {
  const p = node.partido
  const minuto = useLiveMinute(p?.fecha ?? '', p?.estado ?? '')
  const win = ganador(p)
  const live = p?.estado === 'en_juego'
  const jugado = p?.estado === 'finalizado' || live

  return (
    <div
      className={`absolute rounded-xl border px-2.5 py-1.5 flex flex-col justify-between
        ${live
          ? 'border-emerald-400/40 bg-bg-elevated shadow-[0_0_18px_rgba(52,211,153,0.12)]'
          : destacado
            ? 'border-accent/40 bg-bg-elevated shadow-accent'
            : 'border-border bg-bg-elevated/85'
        }`}
      style={{ left: node.x, top: node.y, width: CARD_W, height: CARD_H }}
    >
      {/* Header strip: estado / fecha */}
      <div className="flex items-center justify-between h-3.5">
        {live ? (
          <span className="inline-flex items-center gap-1 text-[9px] font-bold text-emerald-400 uppercase tracking-widest">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
            </span>
            En vivo
          </span>
        ) : (
          <span className="text-[9px] text-content-muted truncate">
            {p
              ? p.estado === 'finalizado' ? 'Finalizado'
                : p.estado === 'postergado' ? 'Postergado'
                : p.estado === 'cancelado' ? 'Cancelado'
                : fechaCorta(p.fecha, tz)
              : 'Por definir'}
          </span>
        )}
        {live && minuto && (
          <span className="text-[10px] font-bold text-emerald-400 tabular-nums">{minuto}</span>
        )}
      </div>

      <TeamLine
        equipo={p?.equipo_local ?? null}
        goles={jugado ? (p?.goles_local ?? 0) : null}
        esGanador={win === 'local'}
        esPerdedor={win === 'visitante'}
        live={live}
      />
      <TeamLine
        equipo={p?.equipo_visitante ?? null}
        goles={jugado ? (p?.goles_visitante ?? 0) : null}
        esGanador={win === 'visitante'}
        esPerdedor={win === 'local'}
        live={live}
      />
    </div>
  )
}

// ── Pan engine ────────────────────────────────────────────────────────────────
// Pointer events unificados + translateX vía rAF. Inercia con fricción
// exponencial (≈ UIScrollView) y rubber-band en los bordes, sin librerías.

const FRICTION = 0.998   // decaimiento de velocidad por ms (deceleración iOS)
const MIN_VEL = 0.02     // px/ms — debajo de esto la inercia se detiene
const MAX_VEL = 4        // px/ms — cap de velocidad al soltar
const RUBBER_DIM = 140   // px — asíntota del overscroll

function rubber(x: number, min: number, max: number): number {
  if (x > max) {
    const over = x - max
    return max + RUBBER_DIM * (1 - 1 / (over / RUBBER_DIM + 1))
  }
  if (x < min) {
    const over = min - x
    return min - RUBBER_DIM * (1 - 1 / (over / RUBBER_DIM + 1))
  }
  return x
}

// ── Main component ────────────────────────────────────────────────────────────

export default function BracketView({ partidos, tz }: Props) {
  const { nodes, links, finalNode, tercero } = useMemo(() => buildLayout(partidos), [partidos])

  const viewportRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const pos = useRef(0)            // translateX actual
  const raf = useRef(0)
  const dragging = useRef(false)
  const dragStart = useRef({ pointer: 0, pos: 0 })
  const samples = useRef<{ t: number; x: number }[]>([])
  const didCenter = useRef(false)
  const [hint, setHint] = useState(true)

  const bounds = () => {
    const vw = viewportRef.current?.clientWidth ?? 0
    if (TOTAL_W <= vw) {
      const c = (vw - TOTAL_W) / 2
      return { min: c, max: c }
    }
    return { min: vw - TOTAL_W, max: 0 }
  }

  const apply = () => {
    if (contentRef.current) {
      contentRef.current.style.transform = `translate3d(${pos.current}px, 0, 0)`
    }
  }

  const stopAnim = () => cancelAnimationFrame(raf.current)

  // Inercia + spring-back, todo en un solo loop de rAF
  const glide = (vel: number) => {
    let v = Math.max(-MAX_VEL, Math.min(MAX_VEL, vel))
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(50, now - last)
      last = now
      const { min, max } = bounds()

      if (pos.current > max || pos.current < min) {
        // Fuera de límites: amortiguación fuerte + spring hacia el borde
        const target = pos.current > max ? max : min
        v *= Math.pow(0.93, dt)
        pos.current += v * dt + (target - pos.current) * (1 - Math.exp(-dt * 0.012))
        if (Math.abs(target - pos.current) < 0.5 && Math.abs(v) < MIN_VEL) {
          pos.current = target
          apply()
          return
        }
      } else {
        pos.current += v * dt
        v *= Math.pow(FRICTION, dt)
        if (Math.abs(v) < MIN_VEL && pos.current <= max && pos.current >= min) {
          apply()
          return
        }
      }
      apply()
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
  }

  const animateTo = (target: number) => {
    stopAnim()
    const from = pos.current
    const start = performance.now()
    const dur = 500
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur)
      const ease = 1 - Math.pow(1 - t, 3)
      pos.current = from + (target - from) * ease
      apply()
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
  }

  function onPointerDown(e: React.PointerEvent) {
    stopAnim()
    dragging.current = true
    dragStart.current = { pointer: e.clientX, pos: pos.current }
    samples.current = [{ t: performance.now(), x: e.clientX }]
    viewportRef.current?.setPointerCapture(e.pointerId)
    if (hint) setHint(false)
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!dragging.current) return
    const { min, max } = bounds()
    const raw = dragStart.current.pos + (e.clientX - dragStart.current.pointer)
    pos.current = rubber(raw, min, max)
    apply()
    const now = performance.now()
    samples.current.push({ t: now, x: e.clientX })
    // Solo conservamos los últimos 100 ms para calcular la velocidad de suelta
    samples.current = samples.current.filter(s => now - s.t < 100)
  }

  function onPointerUp() {
    if (!dragging.current) return
    dragging.current = false
    const s = samples.current
    let vel = 0
    if (s.length >= 2) {
      const first = s[0]
      const lastS = s[s.length - 1]
      const dt = lastS.t - first.t
      if (dt > 0) vel = (lastS.x - first.x) / dt
    }
    glide(vel)
  }

  // Trackpad / mouse wheel horizontal
  useEffect(() => {
    const vp = viewportRef.current
    if (!vp) return
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return
      e.preventDefault()
      stopAnim()
      const { min, max } = bounds()
      pos.current = Math.max(min, Math.min(max, pos.current - e.deltaX))
      apply()
    }
    vp.addEventListener('wheel', onWheel, { passive: false })
    return () => vp.removeEventListener('wheel', onWheel)
  }, [])

  useEffect(() => () => cancelAnimationFrame(raf.current), [])

  // Posición inicial: centrar el partido en vivo más avanzado, o la Final
  useLayoutEffect(() => {
    if (didCenter.current) return
    const vp = viewportRef.current
    if (!vp) return
    didCenter.current = true
    const liveNode = nodes.find(n => n.partido?.estado === 'en_juego')
    const focus = liveNode ?? finalNode
    const { min, max } = bounds()
    pos.current = Math.max(min, Math.min(max, vp.clientWidth / 2 - (focus.x + CARD_W / 2)))
    apply()
  }, [nodes, finalNode])

  const campeon = useMemo(() => {
    const w = ganador(finalNode.partido)
    if (!w || !finalNode.partido) return null
    return w === 'local' ? finalNode.partido.equipo_local : finalNode.partido.equipo_visitante
  }, [finalNode])

  return (
    <div className="relative rounded-2xl border border-border bg-bg-surface overflow-hidden select-none">
      {/* Viewport con pan horizontal */}
      <div
        ref={viewportRef}
        className="relative overflow-hidden cursor-grab active:cursor-grabbing"
        style={{ height: TOTAL_H, touchAction: 'pan-y' }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onDoubleClick={() => {
          const vw = viewportRef.current?.clientWidth ?? 0
          const { min, max } = bounds()
          animateTo(Math.max(min, Math.min(max, vw / 2 - (finalNode.x + CARD_W / 2))))
        }}
      >
        <div
          ref={contentRef}
          className="absolute top-0 left-0 will-change-transform"
          style={{ width: TOTAL_W, height: TOTAL_H }}
        >
          {/* Glow sutil detrás de la columna de la Final */}
          <div
            className="absolute inset-y-0 bg-accent-glow pointer-events-none"
            style={{ left: colX(4) - 70, width: CARD_W + 140 }}
          />

          {/* Conectores */}
          <svg width={TOTAL_W} height={TOTAL_H} className="absolute inset-0 pointer-events-none">
            {links.map((l, i) => (
              <g key={i}>
                {l.active && (
                  <path d={linkPath(l)} fill="none" stroke="rgba(25,70,227,0.30)" strokeWidth={4} />
                )}
                <path
                  d={linkPath(l)}
                  fill="none"
                  stroke={l.active ? 'rgba(25,70,227,0.85)' : 'rgba(255,255,255,0.09)'}
                  strokeWidth={1.5}
                />
              </g>
            ))}
          </svg>

          {/* Etiquetas de ronda */}
          {COL_LABELS.map((label, c) => (
            <div
              key={c}
              className="absolute text-center text-[9px] font-semibold uppercase tracking-[0.16em] text-content-muted"
              style={{ left: colX(c), top: 16, width: CARD_W }}
            >
              {label}
            </div>
          ))}

          {/* Cards */}
          {nodes.map(n => (
            <MatchCard key={n.key} node={n} tz={tz} destacado={n.key === 'FIN'} />
          ))}

          {/* Campeón */}
          {campeon && (
            <div
              className="absolute flex items-center justify-center gap-1.5 text-[10px] font-bold text-amber-300 uppercase tracking-widest"
              style={{ left: colX(4) - 30, top: finalNode.y - 26, width: CARD_W + 60 }}
            >
              🏆 Campeón · {campeon.nombre}
            </div>
          )}

          {/* Tercer puesto */}
          <div
            className="absolute text-center text-[9px] font-semibold uppercase tracking-[0.16em] text-content-muted"
            style={{ left: tercero.x, top: tercero.y - 18, width: CARD_W }}
          >
            Tercer puesto
          </div>
        </div>

        {/* Fades en los bordes */}
        <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-bg-surface to-transparent pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-bg-surface to-transparent pointer-events-none" />

        {/* Hint inicial */}
        <div
          className={`absolute bottom-3 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full bg-bg-overlay/90 border border-border
            text-[10px] text-content-secondary pointer-events-none transition-opacity duration-500 ${hint ? 'opacity-100' : 'opacity-0'}`}
        >
          ⟷ Deslizá para recorrer el cuadro · doble tap vuelve a la Final
        </div>
      </div>
    </div>
  )
}
