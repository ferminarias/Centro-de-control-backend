import { useEffect, useRef, useState } from 'react'

export interface NodisPartidoContext {
  id: number
  equipoLocal: string
  equipoVisitante: string
}

interface Probabilities {
  home_win: string  // e.g. "58%"
  draw: string
  away_win: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  probabilities?: Probabilities | null
}

interface Props {
  open: boolean
  onClose: () => void
  partidoContext: NodisPartidoContext | null
  onClearContext: () => void
}

function renderNodisContent(text: string) {
  return text.split('\n').map((line, i) => {
    if (/^━+$/.test(line)) {
      return <div key={i} className="border-t border-white/20 my-1" />
    }
    if (!line) return <div key={i} className="h-2" />
    return <div key={i}>{line}</div>
  })
}

const WELCOME: Message = {
  role: 'assistant',
  content: 'Soy el Oráculo Nodis ✦\nConsultame sobre cualquier partido del Mundial 2026 y te revelo quién gana.',
}

export default function NodisWidget({ open, onClose, partidoContext, onClearContext }: Props) {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const sentContextRef = useRef<number | null>(null)

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100)
  }, [open])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-send when a new partido context arrives
  useEffect(() => {
    if (!partidoContext || sentContextRef.current === partidoContext.id) return
    sentContextRef.current = partidoContext.id
    sendMessage(`Analizame el partido: ${partidoContext.equipoLocal} vs ${partidoContext.equipoVisitante}`, partidoContext.id)
  }, [partidoContext])

  const sendMessage = async (text?: string, ctxId?: number) => {
    const content = (text ?? input).trim()
    if (!content || loading) return
    setInput('')

    const userMsg: Message = { role: 'user', content }
    setMessages(prev => {
      const next = [...prev, userMsg]
      doFetch(next, ctxId ?? partidoContext?.id ?? null)
      return next
    })
  }

  const doFetch = async (currentMessages: Message[], ctxPartidoId: number | null) => {
    setLoading(true)
    const token = localStorage.getItem('prode_token')
    const history = currentMessages.slice(0, -1).slice(-12)
    const lastMsg = currentMessages[currentMessages.length - 1]

    try {
      const res = await fetch('/api/prode/nodis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          message: lastMsg.content,
          partido_id: ctxPartidoId,
          history: history.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail ?? 'Error')
      }

      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.reply, probabilities: data.probabilities ?? null }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error desconocido'
      setMessages(prev => [...prev, { role: 'assistant', content: `Lo siento, no pude procesar tu consulta: ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Mobile overlay backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div className={`
        fixed top-0 right-0 h-full w-full sm:w-80 z-40 flex flex-col overflow-hidden
        bg-bg-surface border-l border-border
        transition-transform duration-300
        lg:static lg:z-auto lg:translate-x-0 lg:shrink-0
        ${open ? 'translate-x-0' : 'translate-x-full lg:hidden'}
      `}>
        {/* Header */}
        <div style={{ height: 'env(safe-area-inset-top, 0px)' }} className="shrink-0 lg:hidden" />
        <div className="h-14 border-b border-border flex items-center px-4 gap-3 shrink-0">
          <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shrink-0">
            <svg width="20" height="20" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 3L21.5 22H6.5L14 3Z" fill="white" fillOpacity="0.95"/>
              <rect x="4" y="21" width="20" height="3" rx="1.5" fill="white" fillOpacity="0.85"/>
              <path d="M14 11l0.55 1.65h1.75l-1.4 1.0 0.55 1.65-1.45-1.05-1.45 1.05 0.55-1.65-1.4-1.0h1.75z" fill="#1946E3"/>
              <path d="M22 5l0.4 1.2 1.25 0.45-1.25 0.45L22 8.3l-0.4-1.2-1.25-0.45 1.25-0.45z" fill="white" fillOpacity="0.8"/>
              <circle cx="5.5" cy="8.5" r="1" fill="white" fillOpacity="0.5"/>
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-content-primary leading-tight">Oráculo Nodis</p>
            <p className="text-[10px] text-content-muted leading-tight">Asistente IA · Mundial 2026</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-content-muted hover:text-content-primary hover:bg-bg-elevated transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        {/* Match context chip */}
        {partidoContext && (
          <div className="px-3 pt-2.5 shrink-0">
            <div className="flex items-center gap-2 bg-accent/10 border border-accent/25 rounded-lg px-3 py-2">
              <span className="text-[10px] font-semibold text-accent uppercase tracking-wider shrink-0">Partido</span>
              <span className="text-xs text-content-secondary truncate flex-1">
                {partidoContext.equipoLocal} vs {partidoContext.equipoVisitante}
              </span>
              <button onClick={onClearContext} className="text-content-muted hover:text-content-primary text-xs shrink-0">✕</button>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 flex flex-col gap-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} gap-2`}>
              {msg.role === 'assistant' && (
                <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center shrink-0 mt-0.5">
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M6.5 1L10.5 10.5H2.5L6.5 1Z" fill="white" fillOpacity="0.95"/>
                    <rect x="1.5" y="10" width="10" height="2" rx="1" fill="white" fillOpacity="0.85"/>
                    <path d="M6.5 5.5l0.32 1h1.05l-0.85 0.62 0.32 1-0.84-0.61-0.84 0.61 0.32-1-0.85-0.62h1.05z" fill="#1946E3"/>
                  </svg>
                </div>
              )}
              <div className="max-w-[82%] flex flex-col gap-2">
                <div className={`rounded-2xl px-3 py-2.5 text-sm leading-relaxed break-words [overflow-wrap:anywhere] ${
                  msg.role === 'user'
                    ? 'bg-accent text-white rounded-tr-sm'
                    : 'bg-bg-elevated text-content-primary rounded-tl-sm'
                }`}>
                  {msg.role === 'assistant'
                    ? renderNodisContent(msg.content)
                    : <span className="whitespace-pre-wrap">{msg.content}</span>}
                </div>
                {msg.probabilities && partidoContext && (
                  <ProbabilityBar
                    probs={msg.probabilities}
                    home={partidoContext.equipoLocal}
                    away={partidoContext.equipoVisitante}
                  />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start gap-2">
              <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center shrink-0">
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M6.5 1L10.5 10.5H2.5L6.5 1Z" fill="white" fillOpacity="0.95"/>
                  <rect x="1.5" y="10" width="10" height="2" rx="1" fill="white" fillOpacity="0.85"/>
                  <path d="M6.5 5.5l0.32 1h1.05l-0.85 0.62 0.32 1-0.84-0.61-0.84 0.61 0.32-1-0.85-0.62h1.05z" fill="#1946E3"/>
                </svg>
              </div>
              <div className="bg-bg-elevated rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1.5 items-center">
                  {[0, 150, 300].map(delay => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-content-muted animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-3 py-3 border-t border-border shrink-0" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom, 0px))' }}>
          <div className="flex gap-2 items-center">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
              placeholder="Preguntale a Nodis..."
              disabled={loading}
              className="flex-1 bg-bg-elevated text-content-primary text-sm rounded-xl px-3 py-2.5 border border-border focus:outline-none focus:border-accent/50 placeholder:text-content-muted disabled:opacity-50 transition-colors"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              className="w-9 h-9 flex items-center justify-center bg-accent text-white rounded-xl disabled:opacity-40 hover:bg-accent-hover transition-colors shrink-0"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 7h12M8 2l6 5-6 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

function ProbabilityBar({ probs, home, away }: { probs: Probabilities; home: string; away: string }) {
  const parse = (s: string) => parseInt(s.replace('%', ''), 10) || 0
  const hw = parse(probs.home_win)
  const dr = parse(probs.draw)
  const aw = parse(probs.away_win)

  return (
    <div className="bg-bg-elevated rounded-xl px-3 py-2.5 flex flex-col gap-2 border border-border/50">
      <p className="text-[10px] font-semibold text-content-muted uppercase tracking-wider">Probabilidades · footballdata.io</p>
      <div className="flex flex-col gap-1.5">
        {[
          { label: home, pct: hw, color: 'bg-accent' },
          { label: 'Empate', pct: dr, color: 'bg-content-muted' },
          { label: away, pct: aw, color: 'bg-status-loss' },
        ].map(({ label, pct, color }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-[10px] text-content-secondary w-16 truncate shrink-0">{label}</span>
            <div className="flex-1 bg-bg-overlay rounded-full h-1.5 overflow-hidden">
              <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[10px] font-semibold text-content-primary w-8 text-right shrink-0">{pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
