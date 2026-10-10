import { useEffect, useRef, type ReactNode } from 'react'
import { label } from '../api'

const TONE: Record<string, string> = {
  RECOMMENDED_APPROVAL: 'good', APPROVED: 'good', PASS: 'good', SUCCEEDED: 'good',
  RECOMMENDED_REJECTION: 'bad', REJECTED: 'bad', FAIL: 'bad', CRITICAL: 'bad', HIGH: 'bad', FAILED: 'bad', PROCESSING_FAILED: 'bad',
  MORE_INFORMATION_REQUIRED: 'warn', AWAITING_CUSTOMER: 'warn', INDETERMINATE: 'warn', MEDIUM: 'warn', PARTIAL: 'warn',
  HUMAN_REVIEW_REQUIRED: 'review', ESCALATED: 'review', AWAITING_REVIEW: 'review',
  PROCESSING: 'muted', SUBMITTED: 'muted', NOT_APPLICABLE: 'muted', INFO: 'muted', LOW: 'muted',
}

export const Badge = ({ value, text }: { value: string | null; text?: string }) =>
  value ? <span className={`badge ${TONE[value] ?? 'muted'}`}>{text ?? label(value)}</span> : <span className="badge muted">Not reviewed yet</span>

export const Spinner = ({ text = 'Loading…' }: { text?: string }) => <div className="state" role="status"><span className="spin" aria-hidden />{text}</div>

export const ErrorBox = ({ message, retry }: { message: string; retry?: () => void }) => (
  <div className="state error" role="alert">
    <strong>Something went wrong.</strong> {message}
    {retry && <button className="btn small" onClick={retry}>Try again</button>}
  </div>
)

export const Empty = ({ children }: { children: ReactNode }) => <div className="state">{children}</div>

export const Card = ({ title, hint, right, children }: { title?: string; hint?: string; right?: ReactNode; children: ReactNode }) => (
  <section className="card">
    {(title || right) && <header><div>{title && <h2>{title}</h2>}{hint && <p className="muted small hint">{hint}</p>}</div>{right}</header>}
    {children}
  </section>
)

export const Field = ({ k, children }: { k: string; children: ReactNode }) => (
  <div className="kv"><dt>{k}</dt><dd>{children}</dd></div>
)

/** Horizontal progress indicator. `current` is the index of the step the user should work on. */
export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="stepper" aria-label="Progress">
      {steps.map((s, i) => (
        <li key={s} className={i < current ? 'done' : i === current ? 'current' : ''} aria-current={i === current ? 'step' : undefined}>
          <span className="dot">{i < current ? '✓' : i + 1}</span><span className="step-label">{s}</span>
        </li>
      ))}
    </ol>
  )
}

export function Tabs({ tabs, active, onChange }: { tabs: { id: string; label: string; count?: number }[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={active === t.id} className={active === t.id ? 'active' : ''} onClick={() => onChange(t.id)}>
          {t.label}{t.count !== undefined && t.count > 0 && <span className="count">{t.count}</span>}
        </button>
      ))}
    </div>
  )
}

/** Accessible modal built on the native <dialog> (focus trap + Esc come for free). */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const d = ref.current
    if (d && !d.open) d.showModal()
    // No cleanup close(): unmounting removes the element, and calling close() here would fire `onClose`
    // (React StrictMode mounts twice in dev) and immediately dismiss the dialog.
  }, [])
  return (
    <dialog ref={ref} className="modal" onClose={onClose} onClick={(e) => { if (e.target === ref.current) onClose() }}>
      <div className="modal-body">
        <header><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label="Close">✕</button></header>
        {children}
      </div>
    </dialog>
  )
}
