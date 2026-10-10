import { useState } from 'react'
import { api, label } from '../api'
import { Modal, ErrorBox } from '../components/ui'
import type { ClaimDetail, RequestedItem } from '../types'

export const ACTION_TITLE: Record<string, string> = {
  APPROVE: 'Approve this claim', REJECT: 'Decline this claim', REQUEST_INFORMATION: 'Ask the customer for more information',
  ESCALATE: 'Escalate to a senior reviewer', MARK_UNDER_REVIEW: 'Mark as under review',
}
const ITEM_TYPES = ['PURCHASE_INVOICE', 'REPAIR_RECEIPT', 'CUSTOMER_STATEMENT', 'CLAIM_FORM', 'OTHER']
export const RECOMMENDED_ACTION: Record<string, string> = {
  RECOMMENDED_APPROVAL: 'APPROVE', RECOMMENDED_REJECTION: 'REJECT', MORE_INFORMATION_REQUIRED: 'REQUEST_INFORMATION', HUMAN_REVIEW_REQUIRED: 'ESCALATE',
}

const saved = () => { try { return localStorage.getItem('vc_reviewer') ?? '' } catch { return '' } }

export default function DecisionDialog({ d, action, onClose, onDone }: { d: ClaimDetail; action: string; onClose: () => void; onDone: () => void }) {
  const ev = d.latest_evaluation!
  const [reason, setReason] = useState('')
  const [who, setWho] = useState(saved)
  const [items, setItems] = useState<RequestedItem[]>(ev.missing_evidence.length ? ev.missing_evidence : [{ item_type: 'PURCHASE_INVOICE', description: '' }])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [link, setLink] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Matches the backend rule: acting differently from the recommendation is an override and needs a reason.
  const override = ['APPROVE', 'REJECT', 'REQUEST_INFORMATION', 'ESCALATE'].includes(action) && RECOMMENDED_ACTION[ev.recommendation] !== action
  const needReason = action === 'REJECT' || override
  const invalid = (needReason && !reason.trim()) || (action === 'REQUEST_INFORMATION' && items.some((i) => !i.description.trim()))

  const submit = async () => {
    setBusy(true); setErr(null)
    try {
      try { localStorage.setItem('vc_reviewer', who) } catch { /* optional convenience */ }
      const r = await api.post<{ upload_link: { path: string } | null }>(`/claims/${d.claim.id}/decisions`, {
        evaluation_id: ev.id, action, reason: reason.trim() || null, reviewer_label: who.trim() || null,
        requested_items: action === 'REQUEST_INFORMATION' ? items : [],
      })
      if (r.upload_link) setLink(window.location.origin + r.upload_link.path)
      else onDone()
    } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }

  if (link) {
    return (
      <Modal title="Link ready to send" onClose={onDone}>
        <p>Send this link to the customer. They can upload the requested documents without logging in.</p>
        <div className="link-box"><code>{link}</code></div>
        <p className="muted small">It is shown only once, expires automatically, and works only for this claim. You can revoke it from the History tab.</p>
        <div className="actions"><button className="btn" onClick={() => { void navigator.clipboard.writeText(link); setCopied(true) }}>{copied ? 'Copied ✓' : 'Copy link'}</button><button className="btn primary" onClick={onDone}>Done</button></div>
      </Modal>
    )
  }

  return (
    <Modal title={ACTION_TITLE[action]} onClose={onClose}>
      {override && <p className="callout warn-box">This is different from our recommendation ({label(ev.recommendation).toLowerCase()}). Please explain why; your reason is saved with the decision.</p>}
      {action === 'REQUEST_INFORMATION' && (
        <div className="items">
          <p className="small muted">What should the customer provide?</p>
          {items.map((it, i) => (
            <div className="item-row" key={i}>
              <select value={it.item_type} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, item_type: e.target.value } : x)))} aria-label="Document type">
                {ITEM_TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}</select>
              <input value={it.description} placeholder="Describe what you need" onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} aria-label="Description" />
              {items.length > 1 && <button className="icon-btn" onClick={() => setItems(items.filter((_, j) => j !== i))} aria-label="Remove item">✕</button>}
            </div>
          ))}
          <button className="link" onClick={() => setItems([...items, { item_type: 'OTHER', description: '' }])}>+ Add another item</button>
        </div>
      )}
      <label>{needReason ? 'Reason (required)' : 'Note (optional)'}<textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder={action === 'REJECT' ? 'e.g. Accidental damage is excluded under this warranty.' : ''} /></label>
      <label>Your name<input value={who} onChange={(e) => setWho(e.target.value)} placeholder="e.g. A. Reviewer" /></label>
      {err && <ErrorBox message={err} />}
      <div className="actions"><button className="btn" onClick={onClose}>Cancel</button>
        <button className={`btn lg ${action === 'REJECT' ? 'danger' : 'primary'}`} disabled={busy || invalid} onClick={submit}>{busy ? 'Saving…' : action === 'REQUEST_INFORMATION' ? 'Create link' : 'Confirm'}</button></div>
    </Modal>
  )
}
