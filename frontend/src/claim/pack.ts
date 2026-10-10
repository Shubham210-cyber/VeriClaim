import { fmtDay, label, money } from '../api'
import type { ClaimDetail, Evidence, Fact, Finding, Policy } from '../types'

export type Outcome = 'APPROVED' | 'DECLINED' | 'INFO' | 'CLARIFY'

const ACTION_OUTCOME: Record<string, Outcome> = {
  APPROVE: 'APPROVED', REJECT: 'DECLINED', REQUEST_INFORMATION: 'INFO', ESCALATE: 'CLARIFY', MARK_UNDER_REVIEW: 'CLARIFY',
}
const REC_OUTCOME: Record<string, Outcome> = {
  RECOMMENDED_APPROVAL: 'APPROVED', RECOMMENDED_REJECTION: 'DECLINED', MORE_INFORMATION_REQUIRED: 'INFO',
  HUMAN_REVIEW_REQUIRED: 'CLARIFY', PROCESSING_FAILED: 'CLARIFY',
}

/** The letter follows the reviewer's decision; before any decision it is a draft based on the recommendation. */
export function outcomeOf(d: ClaimDetail): { outcome: Outcome; decided: boolean } {
  const last = d.decisions[d.decisions.length - 1]
  if (last && ACTION_OUTCOME[last.action]) return { outcome: ACTION_OUTCOME[last.action], decided: true }
  return { outcome: REC_OUTCOME[d.latest_evaluation?.recommendation ?? ''] ?? 'CLARIFY', decided: false }
}

const clean = (s: string) => s.replace(/\s*\((?:Source|No source fact)[^)]*\)\.?\s*$/, '').trim()

/** Replace internal identifiers (policy IDs, enum codes) with the plain wording users see everywhere else. */
export function friendly(s: string, d: ClaimDetail): string {
  const cover = d.claim.policy_name ?? 'your cover'
  return clean(s)
    .replace(/(?:by |under )?synthetic policy\s+[A-Z0-9][A-Z0-9-]+/gi, `under your cover (${cover})`)
    .replace(/\b[A-Z]{2,}(?:_[A-Z]+)+\b/g, (t) => label(t).toLowerCase())
    .replace(/The reviewer-classified event (.+?) is /i, 'The reported cause of the incident ($1) is ')
}

/** Customer-facing text must never mention fraud: drop any sentence that does. */
export const neutral = (s: string, d: ClaimDetail) => friendly(s, d).split(/(?<=[.!?])\s+/).filter((x) => !/fraud/i.test(x)).join(' ')

export const factMap = (d: ClaimDetail) => {
  const m = new Map<string, Fact>()
  d.claim_record_facts.forEach((f) => m.set(f.id, f))
  d.evidence.forEach((e) => e.facts.forEach((f) => m.set(f.id, f)))
  return m
}

/** "Purchase invoice, page 1" style citations for a finding. */
export function citations(f: Finding, facts: Map<string, Fact>, evidence: Map<string, Evidence>): string[] {
  const out = new Set<string>()
  f.source_fact_ids.forEach((id) => {
    const fact = facts.get(id)
    if (!fact) return
    const ev = fact.evidence_id ? evidence.get(fact.evidence_id) : null
    out.add(ev ? `${label(ev.evidence_type)}${fact.source_page ? `, page ${fact.source_page}` : ''}` : 'the claim details')
  })
  return [...out]
}

export function payoutEstimate(d: ClaimDetail, policy: Policy | undefined) {
  const claimed = d.claim.claimed_amount ? Number(d.claim.claimed_amount) : null
  if (claimed === null || !policy || policy.deductible_amount === null) return null
  const cap = policy.max_claim_amount ? Number(policy.max_claim_amount) : Infinity
  const deductible = Number(policy.deductible_amount)
  return { claimed, cap: Number.isFinite(cap) ? cap : null, deductible, estimate: Math.max(0, Math.min(claimed, cap) - deductible) }
}

export function buildLetter(d: ClaimDetail, policy: Policy | undefined): { subject: string; body: string; outcome: Outcome; decided: boolean } {
  const ev = d.latest_evaluation
  const { outcome, decided } = outcomeOf(d)
  const c = d.claim
  const device = [c.product_brand, c.product_model].filter(Boolean).join(' ') || label(c.product_type)
  const last = d.decisions[d.decisions.length - 1]
  const facts = factMap(d)
  const evidence = new Map(d.evidence.map((e) => [e.id, e]))
  const findings = ev?.findings ?? []
  // The customer only needs pointers to real documents, not "the claim details".
  const documentCites = (f: Finding) => citations(f, facts, evidence).filter((x) => x !== 'the claim details')
  const open = (cats: string[]) => findings.filter((f) => cats.includes(f.category) && ['FAIL', 'INDETERMINATE'].includes(f.result))
  const sign = `Kind regards,\n${last?.reviewer_label || 'The Claims Team'}\nVeriClaim`
  const intro = `Claim reference: ${c.claim_number}\nDevice: ${device}\nCover: ${c.policy_name ?? label(c.claim_type)}${c.incident_date ? `\nIncident date: ${fmtDay(c.incident_date)}` : ''}`
  const bullet = (xs: string[]) => xs.map((x) => `  • ${x}`).join('\n')
  let subject = ''
  let body = ''

  if (outcome === 'APPROVED') {
    subject = `Your claim ${c.claim_number} has been approved`
    const p = payoutEstimate(d, policy)
    body = `Dear customer,\n\nThank you for your patience. We have reviewed your claim and the documents you provided, and we are pleased to confirm that it has been approved.\n\n${intro}\n`
    if (p) {
      body += `\nIllustrative settlement estimate (the final amount is confirmed separately):\n` +
        `  Amount claimed: ${money(String(p.claimed), c.currency)}\n` +
        (p.cap !== null ? `  Maximum payable under your cover: ${money(String(p.cap), c.currency)}\n` : '') +
        `  Excess / deductible: ${money(String(p.deductible), c.currency)}\n` +
        `  Estimated payable: ${money(String(p.estimate), c.currency)}\n`
    }
    body += `\nWe will contact you about the next steps. If any detail above looks wrong, please reply to this message.\n\n${sign}`
  } else if (outcome === 'DECLINED') {
    subject = `Update on your claim ${c.claim_number}`
    const reasons = open(['REJECTION_CANDIDATE']).map((f) => {
      const cites = documentCites(f)
      return `${f.title}. ${neutral(f.explanation, d)}${cites.length ? ` (Based on: ${cites.join('; ')}.)` : ''}`
    })
    // The reviewer's own note stays in the case file: it may contain internal remarks, so it is never pasted into the letter.
    body = `Dear customer,\n\nThank you for your claim. We have carefully reviewed it together with the documents you provided. Unfortunately we are unable to approve it.\n\n${intro}\n\n` +
      (reasons.length ? `Why:\n${bullet(reasons)}\n` : '') +
      `\nIf you believe this is not correct, or you have further documents that may change the outcome, please reply with them and we will look at your claim again.\n\n${sign}`
  } else if (outcome === 'INFO') {
    subject = `We need a little more information for claim ${c.claim_number}`
    const items = (last?.requested_items?.length ? last.requested_items : ev?.missing_evidence ?? [])
    body = `Dear customer,\n\nThank you for your claim. To complete our review we need the following from you:\n\n${bullet(items.map((i) => `${label(i.item_type)}: ${i.description}`)) || '  • (list the items needed)'}\n\n` +
      `You can upload them securely, without logging in, using this link:\n  [paste the upload link here]\n\n(The link expires automatically and works only for this claim.)\n\n${intro}\n\n${sign}`
  } else {
    subject = `We would like to clarify a few details on claim ${c.claim_number}`
    const issues = open(['CONFLICT', 'AMBIGUOUS', 'CLARIFY']).map((f) => {
      const cites = documentCites(f)
      return `${f.title}: ${neutral(f.explanation, d)}${cites.length ? ` (See: ${cites.join('; ')}.)` : ''}`
    })
    body = `Dear customer,\n\nThank you for your claim. While reviewing it we noticed a few details that do not line up and we would like to understand them before going further. This is a routine check.\n\n${intro}\n\n` +
      (issues.length ? `What we would like to clarify:\n${bullet(issues)}\n` : '') +
      `\nCould you reply with a short explanation, or any document that helps? Once we hear from you we will continue the review.\n\n${sign}`
  }
  return { subject, body, outcome, decided }
}
