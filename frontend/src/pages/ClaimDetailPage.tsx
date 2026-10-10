import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { HEADLINES, api, describeEvent, downloadUrl, fmtDate, fmtDay, label, money } from '../api'
import { Badge, Empty, ErrorBox, Field, Panel, Spinner } from '../components/ui'
import type { ClaimDetail, Evidence, Fact, Finding, RequestedItem } from '../types'

const UPLOAD_TYPES = ['PURCHASE_INVOICE', 'REPAIR_RECEIPT', 'CUSTOMER_STATEMENT', 'CLAIM_FORM', 'OTHER']
const MATCH: Record<string, string> = {
  APPROVE: 'RECOMMENDED_APPROVAL', REJECT: 'RECOMMENDED_REJECTION',
  REQUEST_INFORMATION: 'MORE_INFORMATION_REQUIRED', ESCALATE: 'HUMAN_REVIEW_REQUIRED',
}
const ACTIONS: [string, string][] = [
  ['MARK_UNDER_REVIEW', 'Mark as under review'], ['APPROVE', 'Approve claim'], ['REJECT', 'Decline claim'],
  ['REQUEST_INFORMATION', 'Ask customer for more information'], ['ESCALATE', 'Escalate to a senior reviewer'],
]
const TERMINAL = ['APPROVED', 'REJECTED', 'CLOSED']
const DATE_FIELDS = ['purchase_date', 'incident_date', 'repair_date']
const MONEY_FIELDS = ['purchase_amount', 'repair_amount', 'claimed_amount']

const pretty = (f: Fact) => {
  if (f.normalized_value === null) return null
  if (DATE_FIELDS.includes(f.field_name)) return fmtDay(f.normalized_value)
  if (MONEY_FIELDS.includes(f.field_name)) return money(f.normalized_value)
  return f.normalized_value
}

export default function ClaimDetailPage() {
  const { id = '' } = useParams()
  const [d, setD] = useState<ClaimDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [evaluating, setEvaluating] = useState(false)

  const load = useCallback(async () => {
    try { setD(await api.get<ClaimDetail>(`/claims/${id}`)); setErr(null) } catch (e) { setErr((e as Error).message) }
  }, [id])
  useEffect(() => { void load() }, [load])

  const evaluate = async () => {
    setEvaluating(true)
    try { await api.post(`/claims/${id}/evaluate`); await load() } catch (e) { setErr((e as Error).message) } finally { setEvaluating(false) }
  }

  const facts = useMemo(() => {
    const m = new Map<string, Fact>()
    d?.claim_record_facts.forEach((f) => m.set(f.id, f))
    d?.evidence.forEach((e) => e.facts.forEach((f) => m.set(f.id, f)))
    return m
  }, [d])

  if (err && !d) return <ErrorBox message={err} retry={load} />
  if (!d) return <Spinner />
  const { claim: c, latest_evaluation: ev } = d
  const byId = new Map(d.evidence.map((e) => [e.id, e]))
  const device = [c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)
  const head = ev ? HEADLINES[ev.recommendation] : null

  return (
    <>
      <p><Link to="/">← All claims</Link></p>
      <div className="page-head">
        <div>
          <h1>{c.claim_number} <Badge value={c.status} /></h1>
          <p className="muted">{device} · {c.policy_name ?? label(c.claim_type)}</p>
        </div>
        <button className="btn primary" onClick={evaluate} disabled={evaluating}>{evaluating ? 'Reviewing…' : ev ? 'Re-check claim' : 'Review claim'}</button>
      </div>
      {err && <ErrorBox message={err} />}

      <section className={`hero ${head?.tone ?? 'muted'}`} aria-live="polite">
        {!ev ? (
          <><div className="hero-title">Not reviewed yet</div><p>Add the customer's documents, then choose <strong>Review claim</strong>. The system checks them against the cover and explains what it finds.</p></>
        ) : (
          <>
            <div className="hero-title">{head?.title ?? label(ev.recommendation)}</div>
            <p>{head?.text}</p>
            <p className="why"><strong>Why:</strong> {ev.summary}</p>
            {ev.missing_evidence.length > 0 && (
              <ul className="needs">{ev.missing_evidence.map((m, i) => <li key={i}><strong>{label(m.item_type)}:</strong> {m.description}</li>)}</ul>
            )}
            {ev.ai_provider === 'sonnet' && ev.ai_summary && <p className="ai"><strong>AI-assisted summary:</strong> {ev.ai_summary.summary}</p>}
            <p className="muted small">This is decision support. A reviewer makes the final call. Checked {fmtDate(ev.completed_at)}.</p>
          </>
        )}
      </section>

      <div className="cols">
        <div>
          <Panel title="Claim details">
            <dl className="kvs">
              <Field k="Device">{device}</Field>
              <Field k={c.product_type === 'MOBILE_PHONE' ? 'IMEI' : 'Serial number'}>{c.device_identifier ?? '—'}</Field>
              <Field k="What happened">{label(c.event_type)}</Field>
              <Field k="Incident date">{fmtDay(c.incident_date)}</Field>
              <Field k="Amount claimed">{money(c.claimed_amount, c.currency)}</Field>
              <Field k="Repair already done">{c.repair_already_performed ? 'Yes' : 'No'}</Field>
              <Field k="Customer's description">{c.damage_or_failure_description ?? '—'}</Field>
            </dl>
          </Panel>
          <EvidencePanel claimId={c.id} evidence={d.evidence} recordFacts={d.claim_record_facts} onChange={load} />
          <Timeline d={d} />
        </div>
        <div>
          {ev && <FindingsPanel findings={ev.findings} facts={facts} evidence={byId} claimId={c.id} />}
          {ev && <DecisionPanel d={d} reload={load} />}
          <Requests d={d} reload={load} />
        </div>
      </div>
    </>
  )
}

function EvidencePanel({ claimId, evidence, recordFacts, onChange }: { claimId: string; evidence: Evidence[]; recordFacts: Fact[]; onChange: () => void }) {
  const [type, setType] = useState('PURCHASE_INVOICE')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const up = async () => {
    if (!file) return
    setBusy(true); setErr(null)
    try { await api.upload(`/claims/${claimId}/evidence`, file, type); setFile(null); onChange() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <Panel title="Documents" hint="PDF, PNG, JPEG or text files up to 10 MB. Newer uploads are added as new versions; nothing is overwritten.">
      <div className="uploader">
        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Document type">{UPLOAD_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label="Choose file" />
        <button className="btn" onClick={up} disabled={!file || busy}>{busy ? 'Reading document…' : 'Upload'}</button>
      </div>
      {err && <ErrorBox message={err} />}
      {evidence.length === 0 && <Empty>No documents yet. Upload an invoice or other proof to get started.</Empty>}
      {evidence.map((e) => (
        <details key={e.id} className="evidence" open>
          <summary>
            <strong>{label(e.evidence_type)}</strong> <span className="muted small">version {e.version_number}</span>{' '}
            <Badge value={e.extraction_status} text={e.extraction_status === 'SUCCEEDED' ? 'Read successfully' : e.extraction_status === 'PARTIAL' ? 'Partly read' : e.extraction_status === 'FAILED' ? 'Could not read' : 'Reading…'} />
          </summary>
          <p className="small muted">{e.original_filename} · {Math.max(1, Math.round(e.size_bytes / 1024))} KB · uploaded by {label(e.uploaded_by).toLowerCase()} · {fmtDate(e.uploaded_at)} · <a href={downloadUrl(claimId, e.id)} target="_blank" rel="noreferrer">Open original</a></p>
          {e.extraction_status === 'FAILED' && <p className="muted small">The text could not be read from this file. That does not mean the information is missing from the original; a clearer copy may help.</p>}
          {e.extraction_status === 'PARTIAL' && <p className="muted small">The file was read but none of the expected details were recognised.</p>}
          <FactTable facts={e.facts} />
        </details>
      ))}
      <details className="evidence"><summary><strong>Details entered on the claim</strong> <span className="muted small">not read from a document</span></summary><FactTable facts={recordFacts} /></details>
    </Panel>
  )
}

function FactTable({ facts }: { facts: Fact[] }) {
  if (!facts.length) return <p className="muted small">Nothing recognised.</p>
  return (
    <div className="scroll-x"><table className="facts"><thead><tr><th>Detail</th><th>Found</th><th>Understood as</th><th>Confidence</th></tr></thead><tbody>
      {facts.map((f) => {
        const low = f.confidence !== null && f.confidence < 0.8
        return (
          <tr key={f.id}>
            <td>{label(f.field_name)}</td>
            <td>{f.raw_value.length > 90 ? f.raw_value.slice(0, 90) + '…' : f.raw_value}
              {f.source !== 'CLAIM_RECORD' && <div className="snippet small">{label(f.extraction_method)}{f.source_page ? `, page ${f.source_page}` : ''}</div>}</td>
            <td>{pretty(f) ?? <em className="muted">unclear: needs checking</em>}</td>
            <td className={low ? 'low' : ''}>{f.confidence === null || f.source === 'CLAIM_RECORD' ? '—' : `${Math.round(f.confidence * 100)}%${low ? ' (low)' : ''}`}</td>
          </tr>
        )
      })}
    </tbody></table></div>
  )
}

function FindingsPanel({ findings, facts, evidence, claimId }: { findings: Finding[]; facts: Map<string, Fact>; evidence: Map<string, Evidence>; claimId: string }) {
  const [showOk, setShowOk] = useState(false)
  const [tech, setTech] = useState(false)
  const visible = findings.filter((f) => f.result !== 'NOT_APPLICABLE' && f.rule_id !== 'SYS-002_AI_UNAVAILABLE')
  const attention = visible.filter((f) => ['FAIL', 'INDETERMINATE'].includes(f.result) && f.category !== 'NOTE')
  const notes = visible.filter((f) => f.category === 'NOTE' && f.result !== 'PASS')
  const passed = visible.filter((f) => !attention.includes(f) && !notes.includes(f))
  const card = (f: Finding) => (
    <div key={f.id} className={`finding ${f.result.toLowerCase()}`}>
      <div className="row between"><strong>{f.title}</strong><Badge value={f.result} /></div>
      <p>{f.explanation}</p>
      {f.source_fact_ids.length > 0 && (
        <ul className="sources">{f.source_fact_ids.map((fid) => {
          const fact = facts.get(fid); if (!fact) return null
          const ev = fact.evidence_id ? evidence.get(fact.evidence_id) : null
          return <li key={fid}><strong>{label(fact.field_name)}:</strong> {pretty(fact) ?? fact.raw_value} <span className="muted">from</span>{' '}
            {ev ? <><a href={downloadUrl(claimId, ev.id)} target="_blank" rel="noreferrer">{label(ev.evidence_type)}</a>{fact.source_page ? `, page ${fact.source_page}` : ''}</> : 'the claim details'}</li>
        })}</ul>
      )}
      {f.recommended_action && <p className="next"><strong>Suggested next step:</strong> {f.recommended_action}</p>}
      {tech && <div className="rule">Rule reference: {f.rule_id} · severity {f.severity.toLowerCase()}</div>}
    </div>
  )
  return (
    <Panel title="What we found" hint="Every point links back to the document it came from."
      right={<label className="inline small"><input type="checkbox" checked={tech} onChange={(e) => setTech(e.target.checked)} /> Technical details</label>}>
      {attention.length === 0 && <Empty>Nothing needs attention.</Empty>}
      {attention.map(card)}
      {notes.length > 0 && <><h3 className="sub">For your awareness</h3>{notes.map(card)}</>}
      <button className="btn small" onClick={() => setShowOk(!showOk)}>{showOk ? 'Hide' : 'Show'} checks that passed ({passed.length})</button>
      {showOk && passed.map(card)}
    </Panel>
  )
}

function DecisionPanel({ d, reload }: { d: ClaimDetail; reload: () => void }) {
  const ev = d.latest_evaluation!
  const [action, setAction] = useState('MARK_UNDER_REVIEW')
  const [reason, setReason] = useState('')
  const [who, setWho] = useState('')
  const [items, setItems] = useState<RequestedItem[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [link, setLink] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const done = TERMINAL.includes(d.claim.status)
  const override = action in MATCH && MATCH[action] !== ev.recommendation
  const needReason = action === 'REJECT' || override

  const pick = (a: string) => {
    setAction(a)
    if (a === 'REQUEST_INFORMATION' && items.length === 0) setItems(ev.missing_evidence.length ? ev.missing_evidence : [{ item_type: 'OTHER', description: '' }])
  }
  const invalid = (needReason && !reason.trim()) || (action === 'REQUEST_INFORMATION' && (items.length === 0 || items.some((i) => !i.description.trim())))

  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      const r = await api.post<{ upload_link: { path: string } | null }>(`/claims/${d.claim.id}/decisions`, {
        evaluation_id: ev.id, action, reason: reason || null, reviewer_label: who || null,
        requested_items: action === 'REQUEST_INFORMATION' ? items : [],
      })
      if (r.upload_link) setLink(window.location.origin + r.upload_link.path)
      setReason(''); reload()
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }

  return (
    <Panel title="Your decision" hint="Recorded with the date, your name and your reason.">
      {d.decisions.map((x) => (
        <p key={x.id} className="small"><strong>{label(x.action)}</strong> {x.is_override && <span className="badge review">Differs from recommendation</span>} · {x.reviewer_label ?? 'Reviewer'} · {fmtDate(x.created_at)}{x.reason && <> — “{x.reason}”</>}</p>
      ))}
      {link && (
        <div className="note"><strong>Customer upload link</strong> <span className="muted small">(shown once; it expires and can be revoked)</span><br /><code>{link}</code>
          <div><button className="btn small" onClick={() => { void navigator.clipboard.writeText(link); setCopied(true) }}>{copied ? 'Copied ✓' : 'Copy link'}</button></div></div>
      )}
      {done ? <p className="muted">This claim is {label(d.claim.status).toLowerCase()}; no further decisions can be recorded.</p> : (
        <>
          <label>Action
            <select value={action} onChange={(e) => pick(e.target.value)}>{ACTIONS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
          </label>
          {override && <p className="warn small">This differs from the system's recommendation ({label(ev.recommendation).toLowerCase()}). Please give a reason; it will be recorded.</p>}
          {action === 'REQUEST_INFORMATION' && items.map((it, i) => (
            <div className="row" key={i}>
              <select value={it.item_type} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, item_type: e.target.value } : x)))}>{UPLOAD_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
              <input className="grow" placeholder="What should the customer provide?" value={it.description} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} />
              <button className="btn small" onClick={() => setItems(items.filter((_, j) => j !== i))} aria-label="Remove item">✕</button>
            </div>
          ))}
          {action === 'REQUEST_INFORMATION' && <button className="btn small" onClick={() => setItems([...items, { item_type: 'OTHER', description: '' }])}>+ Add another item</button>}
          <label>Reason {needReason ? '(required)' : '(optional)'}<textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <label>Your name<input value={who} onChange={(e) => setWho(e.target.value)} placeholder="e.g. A. Reviewer" /></label>
          {err && <ErrorBox message={err} />}
          <button className="btn primary" disabled={busy || invalid} onClick={submit}>{busy ? 'Saving…' : 'Record decision'}</button>
        </>
      )}
    </Panel>
  )
}

function Requests({ d, reload }: { d: ClaimDetail; reload: () => void }) {
  if (!d.upload_requests.length) return null
  const revoke = async (rid: string) => { await api.post(`/claims/${d.claim.id}/upload-requests/${rid}/revoke`); reload() }
  return (
    <Panel title="Customer upload links">
      {d.upload_requests.map((r) => (
        <div key={r.id} className="row between small">
          <span>{r.requested_items.map((i) => label(i.item_type)).join(', ')} · expires {fmtDate(r.expires_at)} · {r.remaining_uploads} upload{r.remaining_uploads === 1 ? '' : 's'} left {r.revoked && <span className="badge bad">Revoked</span>}</span>
          {!r.revoked && <button className="btn small" onClick={() => revoke(r.id)}>Revoke</button>}
        </div>
      ))}
    </Panel>
  )
}

function Timeline({ d }: { d: ClaimDetail }) {
  return (
    <Panel title="History" hint="A permanent record of everything that happened on this claim.">
      <ol className="timeline">
        {[...d.timeline].reverse().map((t) => {
          const e = describeEvent(t)
          return (
            <li key={t.id}><strong>{e.text}</strong>
              <div className="muted small">{label(t.actor_type === 'SYSTEM' ? 'System' : t.actor_type === 'CUSTOMER_LINK' ? 'Customer' : t.actor_label ?? 'Reviewer')} · {fmtDate(t.created_at)}</div>
              {e.note && <div className="small muted">“{e.note}”</div>}</li>
          )
        })}
      </ol>
    </Panel>
  )
}
