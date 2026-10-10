import { Link } from 'react-router-dom'
import { HEADLINES, fmtDate, label } from '../api'
import type { ClaimDetail } from '../types'
import { RECOMMENDED_ACTION } from './DecisionDialog'

const BTN: [string, string][] = [['APPROVE', 'Approve'], ['REJECT', 'Decline'], ['REQUEST_INFORMATION', 'Ask customer for info']]
const MORE: [string, string][] = [['ESCALATE', 'Escalate to senior reviewer'], ['MARK_UNDER_REVIEW', 'Mark as under review']]
const TERMINAL = ['APPROVED', 'REJECTED', 'CLOSED']

export default function ResultCard({ d, reviewing, onDecide, onReview }: { d: ClaimDetail; reviewing: boolean; onDecide: (a: string) => void; onReview: () => void }) {
  const ev = d.latest_evaluation
  const done = TERMINAL.includes(d.claim.status)
  const last = d.decisions[d.decisions.length - 1]
  const activeLinks = d.upload_requests.filter((r) => !r.revoked && new Date(r.expires_at) > new Date())

  if (reviewing) {
    return <section className="result muted-tone" aria-live="polite"><div className="result-title"><span className="spin" aria-hidden /> Reviewing the claim…</div><p>Reading the documents and checking them against the cover.</p></section>
  }
  if (!ev) {
    return (
      <section className="result muted-tone">
        <div className="result-title">Add documents to start the review</div>
        <p>Upload the customer's invoice in the <strong>Documents</strong> tab. The review runs automatically.</p>
      </section>
    )
  }
  const head = HEADLINES[ev.recommendation]
  const rec = RECOMMENDED_ACTION[ev.recommendation]

  return (
    <section className={`result ${head?.tone ?? 'muted'}-tone`} aria-live="polite">
      <div className="result-top">
        <div>
          <div className="eyebrow">{done ? 'Decision recorded' : 'Our recommendation'}</div>
          <div className="result-title">{head?.title ?? label(ev.recommendation)}</div>
        </div>
        <div className="row">
          {ev.recommendation === 'PROCESSING_FAILED' && <button className="btn" onClick={onReview}>Try again</button>}
          {ev.recommendation !== 'PROCESSING_FAILED' && <Link className="btn" to={`/claims/${d.claim.id}/pack`}>📄 Decision pack</Link>}
        </div>
      </div>
      <p className="why">{ev.summary}</p>
      {ev.missing_evidence.length > 0 && !done && (
        <ul className="needs">{ev.missing_evidence.map((m, i) => <li key={i}><strong>{label(m.item_type)}:</strong> {m.description}</li>)}</ul>
      )}
      {ev.ai_provider === 'sonnet' && ev.ai_summary && <p className="ai"><strong>AI-assisted summary:</strong> {ev.ai_summary.summary}</p>}

      {done && last ? (
        <div className="decided"><strong>{label(last.action)}</strong> by {last.reviewer_label ?? 'a reviewer'} on {fmtDate(last.created_at)}{last.reason && <> · “{last.reason}”</>}</div>
      ) : (
        <>
          {d.claim.status === 'AWAITING_CUSTOMER' && (
            <p className="waiting">⏳ Waiting for the customer to upload documents{activeLinks[0] ? ` (link expires ${fmtDate(activeLinks[0].expires_at)})` : ''}. Their upload will appear here and the claim will be re-checked automatically.</p>
          )}
          <div className="decision-bar">
            <span className="muted small">Your decision:</span>
            {BTN.map(([a, t]) => (
              <button key={a} className={`btn lg ${a === rec ? (a === 'REJECT' ? 'danger' : 'primary') : ''}`} onClick={() => onDecide(a)}>{t}{a === rec && <span className="rec-tag">Recommended</span>}</button>
            ))}
            <details className="more"><summary className="btn lg">More</summary>
              <div className="menu">{MORE.map(([a, t]) => <button key={a} onClick={() => onDecide(a)}>{t}</button>)}</div></details>
          </div>
        </>
      )}
      <p className="muted small fine">Decision support only; a reviewer makes the final call. Checked {fmtDate(ev.completed_at)}.</p>
    </section>
  )
}
