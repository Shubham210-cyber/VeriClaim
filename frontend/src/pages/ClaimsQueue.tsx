import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmtDate, label, money } from '../api'
import { Badge, ErrorBox, Spinner } from '../components/ui'
import type { ClaimSummary } from '../types'

interface Page { items: ClaimSummary[]; total: number }

// What a reviewer actually cares about, instead of nine raw statuses.
const GROUPS: { id: string; title: string; statuses: string[] }[] = [
  { id: 'all', title: 'All', statuses: [] },
  { id: 'action', title: 'Needs your review', statuses: ['SUBMITTED', 'AWAITING_REVIEW', 'ESCALATED', 'PROCESSING_FAILED'] },
  { id: 'waiting', title: 'Waiting for customer', statuses: ['AWAITING_CUSTOMER'] },
  { id: 'done', title: 'Completed', statuses: ['APPROVED', 'REJECTED', 'CLOSED'] },
]

const NEXT: Record<string, string> = {
  SUBMITTED: 'Add documents', AWAITING_REVIEW: 'Review', AWAITING_CUSTOMER: 'Waiting', ESCALATED: 'Review',
  PROCESSING_FAILED: 'Retry', APPROVED: 'View', REJECTED: 'View', CLOSED: 'View',
}

export default function ClaimsQueue() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [device, setDevice] = useState('')
  const [group, setGroup] = useState('all')
  const [data, setData] = useState<Page | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setErr(null)
    const qs = new URLSearchParams({ limit: '100' })
    if (q.trim()) qs.set('q', q.trim())
    if (device) qs.set('product_type', device)
    try { setData(await api.get<Page>(`/claims?${qs}`)) } catch (e) { setErr((e as Error).message) }
  }, [q, device])

  useEffect(() => { const t = setTimeout(() => void load(), 200); return () => clearTimeout(t) }, [load])

  const counts = useMemo(() => Object.fromEntries(GROUPS.map((g) => [g.id,
    (data?.items ?? []).filter((c) => g.id === 'all' || g.statuses.includes(c.status)).length])), [data])
  const rows = (data?.items ?? []).filter((c) => group === 'all' || GROUPS.find((g) => g.id === group)!.statuses.includes(c.status))

  const noClaimsAtAll = data && data.total === 0 && !q && !device

  return (
    <>
      <div className="page-head">
        <div><h1>Claims</h1><p className="muted">Check each claim against its cover and the customer's documents, then decide.</p></div>
        <Link className="btn primary lg" to="/claims/new">+ New claim</Link>
      </div>

      {err && <ErrorBox message={err} retry={load} />}
      {!err && !data && <Spinner />}

      {noClaimsAtAll && (
        <div className="welcome card">
          <h2>Welcome to VeriClaim</h2>
          <ol className="how">
            <li><strong>Add a claim</strong><span>Pick the cover, enter the device and what happened.</span></li>
            <li><strong>Upload documents</strong><span>We read the invoice and check it against the cover.</span></li>
            <li><strong>You decide</strong><span>See a clear recommendation with the evidence behind it.</span></li>
          </ol>
          <div className="row center-row">
            <Link className="btn primary lg" to="/claims/new">Create your first claim</Link>
          </div>
        </div>
      )}

      {data && !noClaimsAtAll && (
        <>
          <div className="toolbar">
            <div className="chips" role="tablist" aria-label="Claim groups">
              {GROUPS.map((g) => (
                <button key={g.id} role="tab" aria-selected={group === g.id} className={`chip ${group === g.id ? 'active' : ''}`} onClick={() => setGroup(g.id)}>
                  {g.title} <span className="count">{counts[g.id]}</span>
                </button>
              ))}
            </div>
            <div className="row">
              <input className="search" placeholder="Search claim number, brand or model" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search claims" />
              <select value={device} onChange={(e) => setDevice(e.target.value)} aria-label="Device">
                <option value="">All devices</option><option value="LAPTOP">Laptops</option><option value="MOBILE_PHONE">Phones</option>
              </select>
            </div>
          </div>

          {rows.length === 0 ? (
            <div className="state">No claims here{q || device ? ' match your search' : ' right now'}.</div>
          ) : (
            <div className="table-wrap">
              <table className="claims">
                <thead><tr><th>Claim</th><th>Device</th><th>Status</th><th>Our recommendation</th><th>Submitted</th><th /></tr></thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.id} onClick={() => nav(`/claims/${c.id}`)} tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') nav(`/claims/${c.id}`) }}>
                      <td><Link to={`/claims/${c.id}`} onClick={(e) => e.stopPropagation()}><strong>{c.claim_number}</strong></Link>
                        <div className="muted small">{c.policy_name ?? label(c.claim_type)}</div></td>
                      <td>{[c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)}
                        {c.claimed_amount && <div className="muted small nowrap">{money(c.claimed_amount, c.currency)} claimed</div>}</td>
                      <td><Badge value={c.status} /></td>
                      <td><Badge value={c.latest_recommendation} /></td>
                      <td className="muted small when">{fmtDate(c.submitted_at)}</td>
                      <td className="go">{NEXT[c.status] ?? 'Open'} →</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </>
  )
}
