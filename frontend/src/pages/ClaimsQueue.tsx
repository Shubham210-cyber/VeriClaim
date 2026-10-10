import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmtDate, label, money } from '../api'
import { Badge, Empty, ErrorBox, Spinner } from '../components/ui'
import type { ClaimSummary } from '../types'

interface Page { items: ClaimSummary[]; total: number }
const STATUSES = ['SUBMITTED', 'AWAITING_REVIEW', 'AWAITING_CUSTOMER', 'APPROVED', 'REJECTED', 'ESCALATED', 'PROCESSING_FAILED']

export default function ClaimsQueue() {
  const [f, setF] = useState({ q: '', status: '', product_type: '', claim_type: '', submitted_from: '', submitted_to: '' })
  const [data, setData] = useState<Page | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setErr(null)
    const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v))
    try {
      setData(await api.get<Page>(`/claims?${qs}`))
    } catch (e) {
      setErr((e as Error).message)
    }
  }, [f])

  useEffect(() => { void load() }, [load])

  const seed = async () => {
    setBusy(true)
    try {
      await api.post('/demo/seed')
      await load()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value })
  const filtered = Object.values(f).some(Boolean)

  return (
    <>
      <div className="page-head">
        <div><h1>Claims</h1><p className="muted">Review warranty and insurance claims for laptops and phones, backed by the customer's documents.</p></div>
        <div className="row">
          <button className="btn" onClick={seed} disabled={busy} title="Adds four sample claims with fake documents">{busy ? 'Adding samples…' : 'Add sample claims'}</button>
          <Link className="btn primary" to="/claims/new">+ New claim</Link>
        </div>
      </div>
      <div className="filters" role="search">
        <input className="grow" placeholder="Search by claim number, brand or model" value={f.q} onChange={set('q')} aria-label="Search claims" />
        <select value={f.status} onChange={set('status')} aria-label="Status">
          <option value="">Any status</option>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <select value={f.product_type} onChange={set('product_type')} aria-label="Device">
          <option value="">Any device</option><option value="LAPTOP">Laptop</option><option value="MOBILE_PHONE">Mobile phone</option>
        </select>
        <select value={f.claim_type} onChange={set('claim_type')} aria-label="Claim type">
          <option value="">Warranty and insurance</option><option value="WARRANTY">Warranty</option><option value="INSURANCE">Insurance</option>
        </select>
        <label className="inline">From <input type="date" value={f.submitted_from} onChange={set('submitted_from')} /></label>
        <label className="inline">To <input type="date" value={f.submitted_to} onChange={set('submitted_to')} /></label>
      </div>
      {err && <ErrorBox message={err} retry={load} />}
      {!err && !data && <Spinner />}
      {data && data.items.length === 0 && (
        <Empty>{filtered ? 'No claims match these filters.' : <>No claims yet. Create one, or choose <strong>Add sample claims</strong> to explore with fake data.</>}</Empty>
      )}
      {data && data.items.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Claim</th><th>Device</th><th>Cover</th><th>Status</th><th>Our recommendation</th><th>Submitted</th></tr></thead>
            <tbody>
              {data.items.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/claims/${c.id}`}><strong>{c.claim_number}</strong></Link>{c.claimed_amount && <div className="muted small">{money(c.claimed_amount, c.currency)}</div>}</td>
                  <td>{[c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)}<div className="muted small">{label(c.product_type)}</div></td>
                  <td>{c.policy_name ?? label(c.claim_type)}</td>
                  <td><Badge value={c.status} /></td>
                  <td><Badge value={c.latest_recommendation} /></td>
                  <td className="muted small">{fmtDate(c.submitted_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted small pad">{data.total} claim{data.total === 1 ? '' : 's'}</div>
        </div>
      )}
    </>
  )
}
