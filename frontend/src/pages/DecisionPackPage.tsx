import { useEffect, useMemo, useState } from 'react'
import { flushSync } from 'react-dom'
import { Link, useParams } from 'react-router-dom'
import { HEADLINES, api, describeEvent, fmtDate, fmtDay, label, money } from '../api'
import { eventLabel } from '../constants'
import { Badge, ErrorBox, Spinner } from '../components/ui'
import { buildLetter, citations, factMap, friendly, payoutEstimate } from '../claim/pack'
import type { ClaimDetail, Policy } from '../types'

type Scope = 'both' | 'letter' | 'file'

export default function DecisionPackPage() {
  const { id = '' } = useParams()
  const [d, setD] = useState<ClaimDetail | null>(null)
  const [policies, setPolicies] = useState<Policy[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [edited, setEdited] = useState(false)
  const [copied, setCopied] = useState(false)
  const [scope, setScope] = useState<Scope>('both')

  useEffect(() => {
    Promise.all([api.get<ClaimDetail>(`/claims/${id}`), api.get<{ items: Policy[] }>('/policies')])
      .then(([detail, p]) => { setD(detail); setPolicies(p.items) })
      .catch((e: Error) => setErr(e.message))
  }, [id])

  const policy = policies.find((p) => p.id === d?.claim.policy_id)
  const draft = useMemo(() => (d ? buildLetter(d, policy) : null), [d, policy])
  useEffect(() => { if (draft && !edited) { setSubject(draft.subject); setBody(draft.body) } }, [draft, edited])

  if (err) return <ErrorBox message={err} />
  if (!d || !draft) return <Spinner />
  const ev = d.latest_evaluation
  if (!ev) return <ErrorBox message="This claim has not been reviewed yet, so there is nothing to put in a decision pack. Add documents first." />

  const c = d.claim
  const facts = factMap(d)
  const evidence = new Map(d.evidence.map((e) => [e.id, e]))
  const device = [c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)
  const issues = ev.findings.filter((f) => ['FAIL', 'INDETERMINATE'].includes(f.result) && f.category !== 'NOTE' && f.rule_id !== 'SYS-002_AI_UNAVAILABLE')
  const notes = ev.findings.filter((f) => f.category === 'NOTE' && f.result !== 'PASS')
  const passed = ev.findings.filter((f) => f.result === 'PASS')
  const last = d.decisions[d.decisions.length - 1]
  const head = HEADLINES[ev.recommendation]
  const p = payoutEstimate(d, policy)
  const clean = (s: string) => friendly(s, d)

  const print = (s: Scope) => { flushSync(() => setScope(s)); window.print(); setScope('both') }
  const copy = async () => { await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`); setCopied(true); setTimeout(() => setCopied(false), 2000) }

  return (
    <div className={`pack scope-${scope}`}>
      <div className="no-print">
        <p className="crumb"><Link to={`/claims/${c.id}`}>← Back to claim</Link></p>
        <div className="page-head tight">
          <div><h1>Decision pack</h1><p className="muted">{device} · {c.claim_number}. A draft customer letter and a printable case file, built from the evidence.</p></div>
          <div className="row">
            <button className="btn" onClick={() => print('file')}>Print case file</button>
            <button className="btn primary" onClick={() => print('letter')}>Print letter</button>
          </div>
        </div>
        {!draft.decided && <div className="callout warn-box">No decision has been recorded yet, so this letter is a draft based on our recommendation. Record your decision first if you want it to reflect your choice.</div>}
      </div>

      <section className="card letter-card">
        <header className="no-print"><div><h2>Customer letter</h2><p className="muted small hint">A draft you can edit before sending. Nothing is sent automatically.</p></div>
          <div className="row">{edited && <button className="btn small" onClick={() => setEdited(false)}>Reset to draft</button>}<button className="btn small" onClick={() => void copy()}>{copied ? 'Copied ✓' : 'Copy text'}</button></div></header>
        <label className="no-print">Subject<input value={subject} onChange={(e) => { setSubject(e.target.value); setEdited(true) }} /></label>
        <label className="no-print">Message<textarea className="letter-text" rows={20} value={body} onChange={(e) => { setBody(e.target.value); setEdited(true) }} /></label>
        {draft.outcome === 'INFO' && <p className="muted small no-print">The upload link is shown only once, when you create it. Paste it where the letter says so.</p>}
        <div className="print-only letter-print"><div className="letter-subject">{subject}</div>{body}</div>
      </section>

      <section className="card casefile">
        <header className="file-head"><div><div className="eyebrow">Case file</div><h2>{c.claim_number} · {device}</h2></div><div className="muted small right">Generated {fmtDate(new Date().toISOString())}<br />Synthetic demo data</div></header>

        <h3 className="file-h">Summary</h3>
        <dl className="kvs compact">
          <div className="kv"><dt>Cover</dt><dd>{c.policy_name}</dd></div>
          <div className="kv"><dt>Device</dt><dd>{device}{c.device_identifier ? ` · ${c.device_identifier}` : ''}</dd></div>
          <div className="kv"><dt>What happened</dt><dd>{eventLabel(c.event_type)}{c.damage_or_failure_description ? ` — ${c.damage_or_failure_description}` : ''}</dd></div>
          <div className="kv"><dt>Incident date</dt><dd>{fmtDay(c.incident_date)}</dd></div>
          <div className="kv"><dt>Amount claimed</dt><dd>{money(c.claimed_amount, c.currency)}</dd></div>
          {p && <div className="kv"><dt>Illustrative estimate</dt><dd>{money(String(p.estimate), c.currency)} <span className="muted small">(claimed, capped at the maximum, less the deductible; not a settlement promise)</span></dd></div>}
        </dl>

        <h3 className="file-h">Recommendation and decision</h3>
        <p><Badge value={ev.recommendation} text={head?.title ?? label(ev.recommendation)} /> {ev.summary}</p>
        {last ? <p><strong>Reviewer decision:</strong> {label(last.action)} by {last.reviewer_label ?? 'a reviewer'} on {fmtDate(last.created_at)}{last.is_override ? ' (differs from the recommendation)' : ''}{last.reason ? ` — “${last.reason}”` : ''}</p>
          : <p className="muted">No reviewer decision recorded yet.</p>}

        <h3 className="file-h">Findings{issues.length ? ` (${issues.length} to look at)` : ''}</h3>
        {issues.length === 0 && <p className="muted">No open issues.</p>}
        {issues.map((f) => (
          <div key={f.id} className="file-finding">
            <div><strong>{f.title}</strong> <Badge value={f.result} /></div>
            <div>{clean(f.explanation)}</div>
            {citations(f, facts, evidence).length > 0 && <div className="muted small">Evidence: {citations(f, facts, evidence).join('; ')}</div>}
          </div>
        ))}
        {notes.map((f) => <div key={f.id} className="file-finding"><div><strong>{f.title}</strong> <span className="muted small">(for awareness)</span></div><div>{clean(f.explanation)}</div></div>)}
        <p className="small"><strong>Checks passed ({passed.length}):</strong> <span className="muted">{passed.map((f) => f.title).join(' · ')}</span></p>

        <h3 className="file-h">Documents reviewed</h3>
        {d.evidence.length === 0 ? <p className="muted">None.</p> : (
          <table className="file-table"><thead><tr><th>Document</th><th>File</th><th>Version</th><th>Uploaded</th><th>Read</th></tr></thead><tbody>
            {d.evidence.map((e) => <tr key={e.id}><td>{label(e.evidence_type)}</td><td>{e.original_filename}</td><td>v{e.version_number}</td><td>{fmtDate(e.uploaded_at)}</td><td>{e.extraction_status === 'SUCCEEDED' ? 'Yes' : label(e.extraction_status)}</td></tr>)}
          </tbody></table>
        )}

        <h3 className="file-h">History</h3>
        <ol className="file-history">
          {d.timeline.map((t) => { const e = describeEvent(t); return <li key={t.id}><span className="muted small">{fmtDate(t.created_at)}</span> {e.text}{e.note ? ` — “${e.note}”` : ''}</li> })}
        </ol>
        <p className="muted small fine">Decision support only: the system checks documents against the cover and cannot decide a claim. All data in this demo is synthetic.</p>
      </section>
    </div>
  )
}
