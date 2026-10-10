import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, label } from '../api'
import { ErrorBox, Spinner } from '../components/ui'
import type { Claim, Policy } from '../types'

const EVENTS = ['MANUFACTURING_DEFECT', 'HARDWARE_FAILURE', 'ACCIDENTAL_DAMAGE', 'LIQUID_DAMAGE', 'THEFT', 'COSMETIC_WEAR', 'OTHER']

export default function NewClaim() {
  const nav = useNavigate()
  const [policies, setPolicies] = useState<Policy[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [v, setV] = useState({
    policy_id: '', product_brand: '', product_model: '', device_identifier: '', event_type: 'OTHER', incident_date: '',
    claimed_amount: '', repair_already_performed: false, damage_or_failure_description: '',
  })

  useEffect(() => {
    api.get<{ items: Policy[] }>('/policies').then((r) => { setPolicies(r.items); setV((x) => ({ ...x, policy_id: r.items[0]?.id ?? '' })) })
      .catch((e: Error) => setErr(e.message))
  }, [])

  if (!policies) return err ? <ErrorBox message={err} /> : <Spinner />
  const policy = policies.find((p) => p.id === v.policy_id)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!policy) return
    setSaving(true); setErr(null)
    try {
      const body = {
        ...v, product_type: policy.product_type, claim_type: policy.claim_type,
        incident_date: v.incident_date || null, claimed_amount: v.claimed_amount || null,
        product_brand: v.product_brand || null, product_model: v.product_model || null,
        device_identifier: v.device_identifier || null, damage_or_failure_description: v.damage_or_failure_description || null,
      }
      const c = await api.post<Claim>('/claims', body)
      nav(`/claims/${c.id}`)
    } catch (x) {
      setErr((x as Error).message); setSaving(false)
    }
  }
  const t = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value })

  return (
    <form className="panel form" onSubmit={submit}>
      <header><h2>New claim</h2></header>
      {err && <ErrorBox message={err} />}
      <label>Synthetic policy
        <select value={v.policy_id} onChange={t('policy_id')}>{policies.map((p) => <option key={p.id} value={p.id}>{p.name} — {p.id}</option>)}</select>
      </label>
      {policy && <p className="muted small">{label(policy.product_type)} · {label(policy.claim_type)} · covers {policy.covered_event_types.map(label).join(', ')} · excludes {policy.excluded_event_types.map(label).join(', ')}. {policy.note}</p>}
      <div className="grid2">
        <label>Brand<input value={v.product_brand} onChange={t('product_brand')} placeholder="Northstar" /></label>
        <label>Model<input value={v.product_model} onChange={t('product_model')} placeholder="N14" /></label>
        <label>Serial / IMEI<input value={v.device_identifier} onChange={t('device_identifier')} /></label>
        <label>Event type (reviewer-classified)
          <select value={v.event_type} onChange={t('event_type')}>{EVENTS.map((x) => <option key={x} value={x}>{label(x)}</option>)}</select>
        </label>
        <label>Incident date<input type="date" value={v.incident_date} onChange={t('incident_date')} /></label>
        <label>Claimed amount (INR)<input inputMode="decimal" value={v.claimed_amount} onChange={t('claimed_amount')} placeholder="12500.00" /></label>
      </div>
      <label className="inline"><input type="checkbox" checked={v.repair_already_performed} onChange={(e) => setV({ ...v, repair_already_performed: e.target.checked })} /> A repair has already been performed</label>
      <label>Damage / failure description<textarea rows={3} value={v.damage_or_failure_description} onChange={t('damage_or_failure_description')} /></label>
      <div className="row"><button className="btn primary" disabled={saving}>{saving ? 'Creating…' : 'Create claim'}</button></div>
    </form>
  )
}
