import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, downloadUrl, fmtDate, label } from '../api'
import { Badge, Empty, ErrorBox, Panel, Spinner } from '../components/ui'
import type { ClaimDetail, Evidence, Fact, Finding, RequestedItem } from '../types'

const UPLOAD_TYPES = ['PURCHASE_INVOICE', 'REPAIR_RECEIPT', 'CUSTOMER_STATEMENT', 'CLAIM_FORM', 'OTHER']
const MATCH: Record<string, string> = {
  APPROVE: 'RECOMMENDED_APPROVAL', REJECT: 'RECOMMENDED_REJECTION',
  REQUEST_INFORMATION: 'MORE_INFORMATION_REQUIRED', ESCALATE: 'HUMAN_REVIEW_REQUIRED',
}
const TERMINAL = ['APPROVED', 'REJECTED', 'CLOSED']

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

  return (
    <>
      <p><Link to="/">← Claims queue</Link></p>
      <div className="page-head">
        <div>
          <h1>{c.claim_number} <Badge value={c.status} /></h1>
          <p className="muted">
            {[c.product_brand, c.product_model].filter(Boolean).join(' ')} · {label(c.product_type)} · {label(c.claim_type)} · policy {c.policy_id} (synthetic v{c.policy_version})
          </p>
        </div>
        <button className="btn primary" onClick={evaluate} disabled={evaluating}>{evaluating ? 'Evaluating…' : ev ? 'Re-run evaluation' : 'Run evaluation'}</button>
      </div>
      {err && <ErrorBox message={err} />}

      <Panel title="Recommendation (decision support, not a decision)" right={ev && <Badge value={ev.recommendation} />}>
        {!ev ? <Empty>Not evaluated yet. Upload evidence, then run the evaluation.</Empty> : (
          <>
            <p>{ev.summary}</p>
            {ev.processing_error_code && <p className="muted">Technical issue: {ev.processing_error_code}. This is not a claim outcome; re-run the evaluation.</p>}
            {ev.ai_summary ? (
              <div className="note"><strong>AI summary ({ev.ai_provider}):</strong> {ev.ai_summary.summary}
                {ev.ai_summary.key_points.length > 0 && <ul>{ev.ai_summary.key_points.map((k) => <li key={k}>{k}</li>)}</ul>}</div>
            ) : <p className="muted small">AI summary: {ev.ai_provider === 'none' ? 'disabled' : 'unavailable — deterministic summary shown'}.</p>}
            <p className="muted small">Policy {ev.policy_id} v{ev.policy_version} · rules v{ev.rules_version} · AI mode: {ev.ai_provider} · evaluated {fmtDate(ev.completed_at)}</p>
          </>
        )}
      </Panel>

      <div className="cols">
        <div>
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
    <Panel title="Evidence">
      <div className="uploader">
        <select value={type} onChange={(e) => setType(e.target.value)} aria-label="Evidence type">{UPLOAD_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label="File" />
        <button className="btn" onClick={up} disabled={!file || busy}>{busy ? 'Uploading…' : 'Upload'}</button>
      </div>
      {err && <ErrorBox message={err} />}
      {evidence.length === 0 && <Empty>No documents uploaded yet.</Empty>}
      {evidence.map((e) => (
        <details key={e.id} className="evidence" open>
          <summary>
            <strong>{label(e.evidence_type)}</strong> v{e.version_number} <Badge value={e.extraction_status} />
            {e.extraction_error_code && <span className="muted small"> {e.extraction_error_code}</span>}
          </summary>
          <p className="small muted">{e.original_filename} · {Math.round(e.size_bytes / 1024)} KB · by {label(e.uploaded_by)} · {fmtDate(e.uploaded_at)} · <a href={downloadUrl(claimId, e.id)} target="_blank" rel="noreferrer">View original</a></p>
          {e.extraction_status === 'FAILED' && <p className="muted small">Text could not be read from this file. That is a technical limitation, not evidence the data is absent.</p>}
          <FactTable facts={e.facts} />
        </details>
      ))}
      <details className="evidence"><summary><strong>Claim record</strong> <span className="muted small">entered by reviewer, not from a document</span></summary><FactTable facts={recordFacts} /></details>
    </Panel>
  )
}

function FactTable({ facts }: { facts: Fact[] }) {
  if (!facts.length) return <p className="muted small">No facts extracted.</p>
  return (
    <table className="facts"><thead><tr><th>Field</th><th>Raw value</th><th>Normalized</th><th>Conf.</th><th>Source</th></tr></thead><tbody>
      {facts.map((f) => (
        <tr key={f.id}>
          <td>{label(f.field_name)}</td><td>{f.raw_value}</td>
          <td>{f.normalized_value ?? <em className="muted">unparsed / ambiguous</em>}</td>
          <td className={f.confidence !== null && f.confidence < 0.8 ? 'low' : ''}>{f.confidence === null ? '—' : f.confidence.toFixed(2)}</td>
          <td className="small">{f.source === 'CLAIM_RECORD' ? 'Claim record' : `${f.extraction_method}${f.source_page ? ` · p.${f.source_page}` : ''}`}{f.source_snippet && f.source !== 'CLAIM_RECORD' && <div className="snippet">“{f.source_snippet}”</div>}</td>
        </tr>
      ))}
    </tbody></table>
  )
}

function FindingsPanel({ findings, facts, evidence, claimId }: { findings: Finding[]; facts: Map<string, Fact>; evidence: Map<string, Evidence>; claimId: string }) {
  const [showOk, setShowOk] = useState(false)
  const attention = findings.filter((f) => ['FAIL', 'INDETERMINATE'].includes(f.result))
  const rest = findings.filter((f) => !attention.includes(f))
  const card = (f: Finding) => (
    <div key={f.id} className={`finding ${f.result.toLowerCase()}`}>
      <div className="row between"><strong>{f.title}</strong><span><Badge value={f.result} /> <Badge value={f.severity} /></span></div>
      <div className="rule">{f.rule_id}</div>
      <p>{f.explanation}</p>
      {f.source_fact_ids.length > 0 && (
        <ul className="sources">{f.source_fact_ids.map((fid) => {
          const fact = facts.get(fid); if (!fact) return null
          const ev = fact.evidence_id ? evidence.get(fact.evidence_id) : null
          return <li key={fid}><strong>{label(fact.field_name)}</strong>: {fact.raw_value} — {ev ? <><a href={downloadUrl(claimId, ev.id)} target="_blank" rel="noreferrer">{label(ev.evidence_type)} v{ev.version_number}</a>{fact.source_page ? `, p.${fact.source_page}` : ''}</> : 'claim record'}</li>
        })}</ul>
      )}
      {f.recommended_action && <p className="next"><strong>Next:</strong> {f.recommended_action}</p>}
    </div>
  )
  return (
    <Panel title="Findings" right={<span className="muted small">{attention.length} need attention</span>}>
      {attention.length === 0 && <Empty>No open findings.</Empty>}
      {attention.map(card)}
      <button className="btn small" onClick={() => setShowOk(!showOk)}>{showOk ? 'Hide' : 'Show'} passed / not applicable ({rest.length})</button>
      {showOk && rest.map(card)}
    </Panel>
  )
}

function DecisionPanel({ d, reload }: { d: ClaimDetail; reload: () => void }) {
  const ev = d.latest_evaluation!
  const [action, setAction] = useState('MARK_UNDER_REVIEW')
  const [reason, setReason] = useState('')
  const [who, setWho] = useState('Reviewer (demo)')
  const [items, setItems] = useState<RequestedItem[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [link, setLink] = useState<string | null>(null)
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
    <Panel title="Reviewer decision">
      {d.decisions.map((x) => (
        <p key={x.id} className="small"><Badge value={x.action} /> {x.is_override && <span className="badge review">Override</span>} by {x.reviewer_label ?? 'reviewer'} · {fmtDate(x.created_at)}{x.reason && <> — “{x.reason}”</>}</p>
      ))}
      {link && <div className="note"><strong>Customer upload link (shown once):</strong><br /><code>{link}</code>
        <div><button className="btn small" onClick={() => void navigator.clipboard.writeText(link)}>Copy</button></div></div>}
      {done ? <p className="muted">This claim is {label(d.claim.status).toLowerCase()}; no further decisions can be recorded.</p> : (
        <>
          <label>Action
            <select value={action} onChange={(e) => pick(e.target.value)}>
              {['APPROVE', 'REJECT', 'REQUEST_INFORMATION', 'ESCALATE', 'MARK_UNDER_REVIEW'].map((a) => <option key={a} value={a}>{label(a)}</option>)}
            </select>
          </label>
          {override && <p className="warn small">This differs from the system recommendation ({label(ev.recommendation)}); a reason is required and the override is audited.</p>}
          {action === 'REQUEST_INFORMATION' && items.map((it, i) => (
            <div className="row" key={i}>
              <select value={it.item_type} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, item_type: e.target.value } : x)))}>{UPLOAD_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
              <input className="grow" placeholder="What should the customer provide?" value={it.description} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} />
              <button className="btn small" onClick={() => setItems(items.filter((_, j) => j !== i))} aria-label="Remove item">✕</button>
            </div>
          ))}
          {action === 'REQUEST_INFORMATION' && <button className="btn small" onClick={() => setItems([...items, { item_type: 'OTHER', description: '' }])}>+ Add item</button>}
          <label>Reason {needReason ? '(required)' : '(recommended)'}<textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <label>Reviewer label<input value={who} onChange={(e) => setWho(e.target.value)} /></label>
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
          <span>{r.requested_items.map((i) => label(i.item_type)).join(', ')} · expires {fmtDate(r.expires_at)} · {r.remaining_uploads} upload(s) left {r.revoked && <Badge value="REJECTED" />}</span>
          {!r.revoked && <button className="btn small" onClick={() => revoke(r.id)}>Revoke</button>}
        </div>
      ))}
    </Panel>
  )
}

function Timeline({ d }: { d: ClaimDetail }) {
  return (
    <Panel title="Timeline (audit log)">
      <ol className="timeline">
        {[...d.timeline].reverse().map((t) => (
          <li key={t.id}><strong>{label(t.event_type)}</strong> <span className="muted small">{label(t.actor_type)}{t.actor_label ? ` (${t.actor_label})` : ''} · {fmtDate(t.created_at)}</span>
            {t.details && 'recommendation' in t.details && <div className="small muted">→ {label(String(t.details.recommendation))}</div>}
            {t.details && 'reason' in t.details && t.details.reason ? <div className="small muted">“{String(t.details.reason)}”</div> : null}</li>
        ))}
      </ol>
    </Panel>
  )
}
