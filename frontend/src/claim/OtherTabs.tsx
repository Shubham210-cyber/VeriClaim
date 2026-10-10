import { api, describeEvent, fmtDate, fmtDay, label, money } from '../api'
import { eventLabel } from '../constants'
import { Card, Empty, Field } from '../components/ui'
import type { ClaimDetail } from '../types'
import { FactList } from './DocumentsTab'

export function DetailsTab({ d }: { d: ClaimDetail }) {
  const c = d.claim
  const device = [c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)
  return (
    <div>
      <dl className="kvs">
        <Field k="Cover">{c.policy_name ?? label(c.claim_type)}</Field>
        <Field k="Device">{device}</Field>
        <Field k={c.product_type === 'MOBILE_PHONE' ? 'IMEI' : 'Serial number'}>{c.device_identifier ?? '—'}</Field>
        <Field k="What happened">{eventLabel(c.event_type)}</Field>
        <Field k="Incident date">{fmtDay(c.incident_date)}</Field>
        <Field k="Amount claimed">{money(c.claimed_amount, c.currency)}</Field>
        <Field k="Repair already done">{c.repair_already_performed ? 'Yes' : 'No'}</Field>
        <Field k="Customer's description">{c.damage_or_failure_description ?? '—'}</Field>
        <Field k="Submitted">{fmtDate(c.submitted_at)}</Field>
      </dl>
      {d.claim_record_facts.length > 0 && <details className="evidence-d"><summary>How these details are used in the checks</summary><FactList facts={d.claim_record_facts} /></details>}
    </div>
  )
}

export function HistoryTab({ d, reload }: { d: ClaimDetail; reload: () => void }) {
  const revoke = async (rid: string) => { await api.post(`/claims/${d.claim.id}/upload-requests/${rid}/revoke`); reload() }
  return (
    <div>
      {d.upload_requests.length > 0 && (
        <Card title="Customer upload links">
          {d.upload_requests.map((r) => {
            const expired = new Date(r.expires_at) < new Date()
            return (
              <div key={r.id} className="link-row">
                <span>{r.requested_items.map((i) => label(i.item_type)).join(', ')}<span className="muted small"> · {r.revoked ? 'revoked' : expired ? 'expired' : `expires ${fmtDate(r.expires_at)}`} · {r.remaining_uploads} upload{r.remaining_uploads === 1 ? '' : 's'} left</span></span>
                {!r.revoked && !expired && <button className="btn small" onClick={() => revoke(r.id)}>Revoke</button>}
              </div>
            )
          })}
        </Card>
      )}
      <h4 className="sub">Everything that happened on this claim</h4>
      {d.timeline.length === 0 ? <Empty>Nothing yet.</Empty> : (
        <ol className="timeline">
          {[...d.timeline].reverse().map((t) => {
            const e = describeEvent(t)
            const who = t.actor_type === 'SYSTEM' ? 'System' : t.actor_type === 'CUSTOMER_LINK' ? 'Customer' : t.actor_label ?? 'Reviewer'
            return <li key={t.id}><strong>{e.text}</strong><div className="muted small">{who} · {fmtDate(t.created_at)}</div>{e.note && <div className="small muted">“{e.note}”</div>}</li>
          })}
        </ol>
      )}
    </div>
  )
}
