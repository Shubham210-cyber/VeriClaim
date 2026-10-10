import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api, label } from '../api'
import { documentSlots } from '../constants'
import { Badge, Card, ErrorBox, Spinner, Stepper, Tabs } from '../components/ui'
import DecisionDialog from '../claim/DecisionDialog'
import DocumentsTab from '../claim/DocumentsTab'
import FindingsTab from '../claim/FindingsTab'
import { DetailsTab, HistoryTab } from '../claim/OtherTabs'
import ResultCard from '../claim/ResultCard'
import type { ClaimDetail, Fact, Policy } from '../types'

const TERMINAL = ['APPROVED', 'REJECTED', 'CLOSED']

export default function ClaimDetailPage() {
  const { id = '' } = useParams()
  const notice = (useLocation().state as { notice?: string | null } | null)?.notice ?? null
  const [d, setD] = useState<ClaimDetail | null>(null)
  const [policies, setPolicies] = useState<Policy[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [reviewing, setReviewing] = useState(false)
  const [busyType, setBusyType] = useState<string | null>(null)
  const [tabPick, setTabPick] = useState<string | null>(null)
  const [action, setAction] = useState<string | null>(null)
  const autoRan = useRef(false)

  const load = useCallback(async () => {
    try { setD(await api.get<ClaimDetail>(`/claims/${id}`)); setErr(null) } catch (e) { setErr((e as Error).message) }
  }, [id])
  useEffect(() => { void load() }, [load])
  useEffect(() => { api.get<{ items: Policy[] }>('/policies').then((r) => setPolicies(r.items)).catch(() => undefined) }, [])

  const review = useCallback(async () => {
    setReviewing(true)
    try { await api.post(`/claims/${id}/evaluate`); await load() } catch (e) { setErr((e as Error).message) } finally { setReviewing(false) }
  }, [id, load])

  // Documents added since the last review (e.g. by the customer or another reviewer) trigger a fresh review.
  useEffect(() => {
    if (!d || autoRan.current || d.evidence.length === 0) return
    const ev = d.latest_evaluation
    const newest = Math.max(...d.evidence.map((e) => Date.parse(e.uploaded_at)))
    if (!ev || (ev.completed_at && newest > Date.parse(ev.completed_at))) { autoRan.current = true; void review() }
  }, [d, review])

  const upload = async (file: File, type: string) => {
    setBusyType(type); setErr(null)
    try {
      await api.upload(`/claims/${id}/evidence`, file, type)
      setBusyType(null); autoRan.current = true
      await review()
    } catch (e) { setErr((e as Error).message); setBusyType(null) }
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
  const policy = policies.find((p) => p.id === c.policy_id)
  const slots = documentSlots(policy, c.repair_already_performed)
  const device = [c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)
  const issues = ev ? ev.findings.filter((f) => ['FAIL', 'INDETERMINATE'].includes(f.result) && f.category !== 'NOTE' && f.rule_id !== 'SYS-002_AI_UNAVAILABLE').length : 0
  const tab = tabPick ?? (ev ? 'findings' : 'documents')
  const step = TERMINAL.includes(c.status) ? 3 : ev ? 2 : d.evidence.length > 0 ? 1 : 0

  return (
    <>
      <p className="crumb"><Link to="/">← All claims</Link></p>
      <div className="page-head tight">
        <div>
          <h1>{device} <span className="muted light">{c.claim_number}</span></h1>
          <p className="muted">{c.policy_name ?? label(c.claim_type)} · <Badge value={c.status} /></p>
        </div>
      </div>
      <Stepper steps={['Add documents', 'Review', 'Your decision']} current={step} />
      {notice && <div className="callout warn-box">{notice}</div>}
      {err && <ErrorBox message={err} />}

      <ResultCard d={d} reviewing={reviewing} onDecide={setAction} onReview={() => void review()} />

      <Card>
        <Tabs active={tab} onChange={setTabPick} tabs={[
          { id: 'findings', label: 'What we found', count: issues },
          { id: 'documents', label: 'Documents', count: d.evidence.length },
          { id: 'details', label: 'Claim details' },
          { id: 'history', label: 'History' },
        ]} />
        <div className="tab-panel" role="tabpanel">
          {tab === 'findings' && (ev ? <FindingsTab findings={ev.findings} facts={facts} evidence={new Map(d.evidence.map((e) => [e.id, e]))} claimId={c.id} />
            : <p className="muted">Nothing to show yet. Add the customer's documents in the Documents tab and the review will run automatically.</p>)}
          {tab === 'documents' && <DocumentsTab claimId={c.id} slots={slots} evidence={d.evidence} busyType={busyType} onUpload={(f, t) => void upload(f, t)} />}
          {tab === 'details' && <DetailsTab d={d} />}
          {tab === 'history' && <HistoryTab d={d} reload={() => void load()} />}
        </div>
      </Card>

      {action && ev && <DecisionDialog d={d} action={action} onClose={() => setAction(null)} onDone={() => { setAction(null); void load() }} />}
    </>
  )
}
