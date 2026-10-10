import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, label } from '../api'
import { ACCEPT, EVENT_OPTIONS, documentSlots } from '../constants'
import { ErrorBox, Spinner, Stepper } from '../components/ui'
import type { Claim, Policy } from '../types'

const STEPS = ['Choose cover', 'Device & incident', 'Documents']

export default function NewClaim() {
  const nav = useNavigate()
  const [policies, setPolicies] = useState<Policy[] | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const [phase, setPhase] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [policyId, setPolicyId] = useState('')
  const [v, setV] = useState({
    product_brand: '', product_model: '', device_identifier: '', event_type: '', incident_date: '',
    claimed_amount: '', repair_already_performed: false, damage_or_failure_description: '',
  })
  const [files, setFiles] = useState<Record<string, File | null>>({})

  useEffect(() => {
    api.get<{ items: Policy[] }>('/policies').then((r) => setPolicies(r.items)).catch((e: Error) => setLoadErr(e.message))
  }, [])

  const policy = policies?.find((p) => p.id === policyId)
  const slots = useMemo(() => documentSlots(policy, v.repair_already_performed), [policy, v.repair_already_performed])
  const isPhone = policy?.product_type === 'MOBILE_PHONE'
  const isInsurance = policy?.claim_type === 'INSURANCE'

  if (loadErr) return <ErrorBox message={loadErr} />
  if (!policies) return <Spinner />

  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value })

  const missingDetails = [
    !v.product_brand.trim() && 'brand', !v.product_model.trim() && 'model', !v.device_identifier.trim() && (isPhone ? 'IMEI' : 'serial number'),
    !v.event_type && 'what happened', !v.incident_date && 'incident date',
  ].filter(Boolean) as string[]
  const missingDocs = slots.filter((s) => s.required && !files[s.type])

  const submit = async () => {
    if (!policy) return
    setErr(null)
    try {
      setPhase('Creating the claim…')
      const c = await api.post<Claim>('/claims', {
        policy_id: policy.id, product_type: policy.product_type, claim_type: policy.claim_type,
        product_brand: v.product_brand.trim(), product_model: v.product_model.trim(), device_identifier: v.device_identifier.trim(),
        event_type: v.event_type, incident_date: v.incident_date, claimed_amount: isInsurance && v.claimed_amount ? v.claimed_amount : null,
        repair_already_performed: isInsurance && v.repair_already_performed, damage_or_failure_description: v.damage_or_failure_description.trim() || null,
      })
      const chosen = slots.filter((s) => files[s.type])
      const failed: string[] = []
      for (const s of chosen) {
        setPhase(`Reading your ${s.title.toLowerCase()}…`)
        try { await api.upload(`/claims/${c.id}/evidence`, files[s.type]!, s.type) } catch (e) { failed.push(`${s.title}: ${(e as Error).message}`) }
      }
      if (chosen.length > failed.length) { setPhase('Checking the claim against the cover…'); await api.post(`/claims/${c.id}/evaluate`) }
      nav(`/claims/${c.id}`, { state: { notice: failed.length ? `Claim created, but some documents could not be added. ${failed.join(' ')}` : null } })
    } catch (e) {
      setErr((e as Error).message); setPhase(null)
    }
  }

  if (phase) return <div className="card progress-card"><span className="spin big" aria-hidden /><h2>{phase}</h2><p className="muted">This takes a few seconds.</p></div>

  return (
    <div className="wizard">
      <p><Link to="/">← All claims</Link></p>
      <h1>New claim</h1>
      <Stepper steps={STEPS} current={step} />
      {err && <ErrorBox message={err} />}

      {step === 0 && (
        <section className="card">
          <h2>What is the customer claiming under?</h2>
          <p className="muted small hint">Choose the cover. This decides which documents and rules apply.</p>
          <div className="cover-grid" role="radiogroup" aria-label="Cover">
            {policies.map((p) => (
              <label key={p.id} className={`cover ${policyId === p.id ? 'selected' : ''}`}>
                <input type="radio" name="cover" checked={policyId === p.id} onChange={() => setPolicyId(p.id)} />
                <span className="cover-title">{p.name}</span>
                <span className="cover-line"><b>Covers:</b> {p.covered_event_types.map(label).join(', ')}</span>
                <span className="cover-line"><b>Not covered:</b> {p.excluded_event_types.map(label).join(', ')}</span>
              </label>
            ))}
          </div>
          <div className="actions"><Link className="btn" to="/">Cancel</Link><button className="btn primary lg" disabled={!policy} onClick={() => setStep(1)}>Continue</button></div>
        </section>
      )}

      {step === 1 && policy && (
        <section className="card">
          <h2>Device and incident</h2>
          <p className="muted small hint">{policy.name}. Fields marked * are needed for the review.</p>
          <div className="grid2">
            <label>Brand *<input value={v.product_brand} onChange={set('product_brand')} placeholder="e.g. Northstar" /></label>
            <label>Model *<input value={v.product_model} onChange={set('product_model')} placeholder="e.g. N14" /></label>
            <label>{isPhone ? 'IMEI' : 'Serial number'} *<input value={v.device_identifier} onChange={set('device_identifier')} /></label>
            <label>Incident date *<input type="date" value={v.incident_date} onChange={set('incident_date')} /></label>
          </div>
          <label>What happened? *
            <select value={v.event_type} onChange={set('event_type')}>
              <option value="">Choose one…</option>{EVENT_OPTIONS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
            </select>
          </label>
          {isInsurance && (
            <div className="grid2">
              <label>Amount claimed (INR)<input inputMode="decimal" value={v.claimed_amount} onChange={set('claimed_amount')} placeholder="e.g. 12500.00" /></label>
              <label className="check"><input type="checkbox" checked={v.repair_already_performed} onChange={(e) => setV({ ...v, repair_already_performed: e.target.checked })} /> A repair has already been done</label>
            </div>
          )}
          <label>Describe it in the customer's words<textarea rows={3} value={v.damage_or_failure_description} onChange={set('damage_or_failure_description')} /></label>
          <div className="actions">
            <button className="btn" onClick={() => setStep(0)}>Back</button>
            <button className="btn primary lg" disabled={missingDetails.length > 0} onClick={() => setStep(2)}>Continue</button>
          </div>
          {missingDetails.length > 0 && <p className="muted small right">Still needed: {missingDetails.join(', ')}.</p>}
        </section>
      )}

      {step === 2 && policy && (
        <section className="card">
          <h2>Add the customer's documents</h2>
          <p className="muted small hint">Photos, scans, PDFs or text files up to 10 MB. You can also add them later from the claim page.</p>
          <ul className="slots">
            {slots.map((s) => (
              <li key={s.type} className={files[s.type] ? 'filled' : ''}>
                <div className="slot-text"><strong>{s.title}</strong> <span className={`tag ${s.required ? 'req' : ''}`}>{s.required ? 'Required' : 'Optional'}</span><div className="muted small">{s.hint}</div></div>
                <div className="slot-action">
                  {files[s.type] ? <><span className="file-name">✓ {files[s.type]!.name}</span><button className="link" onClick={() => setFiles({ ...files, [s.type]: null })}>Remove</button></>
                    : <label className="btn small file-btn">Choose file<input type="file" accept={ACCEPT} hidden onChange={(e) => setFiles({ ...files, [s.type]: e.target.files?.[0] ?? null })} /></label>}
                </div>
              </li>
            ))}
          </ul>
          <div className="actions">
            <button className="btn" onClick={() => setStep(1)}>Back</button>
            <button className="btn primary lg" onClick={submit}>{Object.values(files).some(Boolean) ? 'Create claim and review' : 'Create claim'}</button>
          </div>
          {missingDocs.length > 0 && <p className="muted small right">Missing: {missingDocs.map((s) => s.title.toLowerCase()).join(', ')}. You can still continue; the review will ask for it.</p>}
        </section>
      )}
    </div>
  )
}
