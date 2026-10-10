import type { ReactNode } from 'react'
import { label } from '../api'

const TONE: Record<string, string> = {
  RECOMMENDED_APPROVAL: 'good', APPROVED: 'good', PASS: 'good',
  RECOMMENDED_REJECTION: 'bad', REJECTED: 'bad', FAIL: 'bad', CRITICAL: 'bad', HIGH: 'bad',
  MORE_INFORMATION_REQUIRED: 'warn', AWAITING_CUSTOMER: 'warn', INDETERMINATE: 'warn', MEDIUM: 'warn',
  HUMAN_REVIEW_REQUIRED: 'review', ESCALATED: 'review', AWAITING_REVIEW: 'review',
  PROCESSING_FAILED: 'bad', PROCESSING: 'muted', SUBMITTED: 'muted', NOT_APPLICABLE: 'muted', INFO: 'muted', LOW: 'muted',
}

export const Badge = ({ value }: { value: string | null }) =>
  value ? <span className={`badge ${TONE[value] ?? 'muted'}`}>{label(value)}</span> : <span className="badge muted">Not evaluated</span>

export const Spinner = ({ text = 'Loading…' }: { text?: string }) => <div className="state" role="status">{text}</div>

export const ErrorBox = ({ message, retry }: { message: string; retry?: () => void }) => (
  <div className="state error" role="alert">
    <strong>Something went wrong.</strong> {message}
    {retry && <button className="btn small" onClick={retry}>Retry</button>}
  </div>
)

export const Empty = ({ children }: { children: ReactNode }) => <div className="state">{children}</div>

export const Panel = ({ title, children, right }: { title: string; children: ReactNode; right?: ReactNode }) => (
  <section className="panel">
    <header><h2>{title}</h2>{right}</header>
    {children}
  </section>
)
