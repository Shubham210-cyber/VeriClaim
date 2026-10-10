import type { AuditEvent } from './types'

export class ApiError extends Error {
  code: string
  status: number
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError(0, 'NETWORK', 'Cannot reach the server. Please check that the service is running and try again.')
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const e = body?.error
    throw new ApiError(res.status, e?.code ?? 'ERROR', e?.message ?? `Request failed (${res.status})`)
  }
  return body as T
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: data === undefined ? undefined : JSON.stringify(data),
})

export const api = {
  get: <T>(p: string, headers?: Record<string, string>) => request<T>(`/api/v1${p}`, { headers }),
  post: <T>(p: string, data?: unknown) => request<T>(`/api/v1${p}`, json('POST', data)),
  upload: <T>(p: string, file: File, evidenceType: string, headers: Record<string, string> = {}) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('evidence_type', evidenceType)
    return request<T>(`/api/v1${p}`, { method: 'POST', body: fd, headers })
  },
}

export const downloadUrl = (claimId: string, evidenceId: string) => `/api/v1/claims/${claimId}/evidence/${evidenceId}/download`

/** Plain-language wording for every enum value the UI shows. Falls back to Sentence case. */
const WORDS: Record<string, string> = {
  RECOMMENDED_APPROVAL: 'Recommend approval', RECOMMENDED_REJECTION: 'Recommend decline',
  MORE_INFORMATION_REQUIRED: 'More info needed', HUMAN_REVIEW_REQUIRED: 'Needs human review',
  PROCESSING_FAILED: 'Review failed', PROCESSING: 'Reviewing…',
  AWAITING_REVIEW: 'Awaiting review', AWAITING_CUSTOMER: 'Waiting for customer', SUBMITTED: 'New',
  PASS: 'Passed', FAIL: 'Issue found', INDETERMINATE: "Couldn't verify", NOT_APPLICABLE: 'Not applicable',
  MOBILE_PHONE: 'Mobile phone', CUSTOMER_LINK: 'Customer (upload link)', MARK_UNDER_REVIEW: 'Mark as under review',
  REQUEST_INFORMATION: 'Request information', CLAIM_FORM: 'Claim form', PURCHASE_INVOICE: 'Purchase invoice',
  REPAIR_RECEIPT: 'Repair receipt', CUSTOMER_STATEMENT: 'Customer statement', WARRANTY_DOCUMENT: 'Warranty document',
  POLICY_DOCUMENT: 'Policy document', OTHER: 'Other', OCR: 'Read from image', REGEX: 'Read from text', MANUAL: 'Entered by reviewer',
  device_identifier: 'Serial / IMEI', purchase_amount: 'Invoice total', repair_amount: 'Repair cost', claimed_amount: 'Claimed amount',
  event_description: 'Description', product_model: 'Product model', purchase_date: 'Purchase date', incident_date: 'Incident date',
  repair_date: 'Repair date', currency: 'Currency',
}
export const label = (s: string | null | undefined) =>
  !s ? '—' : (WORDS[s] ?? s.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()))
export const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '—'
export const fmtDay = (s: string | null | undefined) => (s ? new Date(s + 'T00:00:00').toLocaleDateString(undefined, { dateStyle: 'medium' }) : '—')
export const money = (amount: string | null | undefined, cur = 'INR') =>
  amount ? new Intl.NumberFormat(undefined, { style: 'currency', currency: cur }).format(Number(amount)) : '—'

export const HEADLINES: Record<string, { title: string; text: string; tone: string }> = {
  RECOMMENDED_APPROVAL: { title: 'Recommended: approve', tone: 'good', text: 'Required evidence is present and every applicable check passed.' },
  RECOMMENDED_REJECTION: { title: 'Recommended: decline', tone: 'bad', text: 'A policy exclusion or eligibility rule clearly applies. A reviewer should confirm before declining.' },
  MORE_INFORMATION_REQUIRED: { title: 'More information needed', tone: 'warn', text: 'Something required is missing or could not be read. Ask the customer for it.' },
  HUMAN_REVIEW_REQUIRED: { title: 'Needs your judgement', tone: 'review', text: 'The evidence conflicts or is ambiguous, so the system will not decide.' },
  PROCESSING_FAILED: { title: 'Review could not be completed', tone: 'bad', text: 'A technical problem stopped the review. This is not a claim outcome; run the evaluation again.' },
}

export function describeEvent(t: AuditEvent): { text: string; note?: string } {
  const d = t.details as Record<string, string | number | boolean | undefined>
  switch (t.event_type) {
    case 'CLAIM_CREATED': return { text: 'Claim created' }
    case 'EVIDENCE_UPLOADED':
      return { text: `${label(String(d.evidence_type))} uploaded (version ${d.version})`, note: d.extraction_status === 'FAILED' ? 'Text could not be read from this file' : undefined }
    case 'EVALUATION_COMPLETED': return { text: `Review completed: ${label(String(d.recommendation))}` }
    case 'EVALUATION_FAILED': return { text: 'Review could not be completed (technical issue)' }
    case 'REVIEWER_DECISION':
      return { text: `Decision recorded: ${label(String(d.action))}${d.is_override ? ' (differs from recommendation)' : ''}`, note: d.reason ? String(d.reason) : undefined }
    case 'UPLOAD_LINK_CREATED': return { text: 'Customer upload link created' }
    case 'UPLOAD_LINK_REVOKED': return { text: 'Customer upload link revoked' }
    case 'CUSTOMER_UPLOAD_ACCEPTED': return { text: 'Customer uploaded a document' }
    default: return { text: label(t.event_type) }
  }
}
