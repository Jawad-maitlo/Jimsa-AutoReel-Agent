import { AlertCircle, Check, Info, X } from 'lucide-react'
import { useEffect } from 'react'
import type { ReactNode } from 'react'

export function StatusPill({ status }: { status: string }) {
  return <span className={`status status-${status}`}><span className="status-dot" />{status.replaceAll('_', ' ')}</span>
}

export function EmptyState({ icon, title, description, action }: { icon: ReactNode; title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{description}</p>{action}</div>
}

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return <span className="spinner-wrap"><span className="spinner" aria-hidden="true" /><span>{label}</span></span>
}

export function ProgressBar({ value }: { value: number }) {
  return <div className="progress-track" role="progressbar" aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
}

export function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])
  return <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
      <header className="modal-header"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={19} /></button></header>
      <div className="modal-body">{children}</div>
    </section>
  </div>
}

export type ToastMessage = { id: number; kind: 'success' | 'error' | 'info'; text: string }
export function Toasts({ messages, dismiss }: { messages: ToastMessage[]; dismiss: (id: number) => void }) {
  return <div className="toasts" aria-live="polite">{messages.map(message => <div className={`toast toast-${message.kind}`} key={message.id}>
    {message.kind === 'success' ? <Check size={18} /> : message.kind === 'error' ? <AlertCircle size={18} /> : <Info size={18} />}
    <span>{message.text}</span><button onClick={() => dismiss(message.id)} aria-label="Dismiss notification"><X size={15} /></button>
  </div>)}</div>
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint && <span className="field-hint">{hint}</span>}</label>
}
