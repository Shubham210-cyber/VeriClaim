import type { ReactNode } from 'react'
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

export const Panel = ({ title, children, right, hint }: { title: string; children: ReactNode; right?: ReactNode; hint?: string }) => (
  <section className="panel">
    <header><div><h2>{title}</h2>{hint && <p className="muted small hint">{hint}</p>}</div>{right}</header>
    {children}
  </section>
)

export const Field = ({ k, children }: { k: string; children: ReactNode }) => (
  <div className="kv"><dt>{k}</dt><dd>{children}</dd></div>
)
