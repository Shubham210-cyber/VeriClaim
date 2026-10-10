export interface ClaimSummary {
  id: string; claim_number: string; product_type: string; product_brand: string | null; product_model: string | null
  claim_type: string; policy_id: string; status: string; event_type: string | null; submitted_at: string
  latest_recommendation: string | null; claimed_amount: string | null; currency: string
}
export interface Claim extends ClaimSummary {
  policy_version: string; device_identifier: string | null; repair_already_performed: boolean
  incident_date: string | null; damage_or_failure_description: string | null
}
export interface Fact {
  id: string; evidence_id: string | null; source: string; field_name: string; raw_value: string
  normalized_value: string | null; confidence: number | null; source_page: number | null
  source_snippet: string | null; extraction_method: string
}
export interface Evidence {
  id: string; evidence_type: string; original_filename: string; mime_type: string; size_bytes: number
  version_number: number; uploaded_by: string; uploaded_at: string; extraction_status: string
  extraction_error_code: string | null; facts: Fact[]
}
export interface Finding {
  id: string; rule_id: string; severity: string; result: string; category: string; title: string
  explanation: string; evidence_ids: string[]; source_fact_ids: string[]; recommended_action: string | null
}
export interface RequestedItem { item_type: string; description: string }
export interface AiSummary { summary: string; key_points: string[]; cited_rule_ids: string[] }
export interface Evaluation {
  id: string; recommendation: string; reason_codes: string[]; missing_evidence: RequestedItem[]; summary: string
  ai_summary: AiSummary | null; ai_provider: string; rules_version: string; policy_id: string; policy_version: string
  completed_at: string | null; processing_error_code: string | null; findings: Finding[]
}
export interface Decision {
  id: string; action: string; reason: string | null; is_override: boolean; reviewer_label: string | null
  created_at: string; requested_items: RequestedItem[]
}
export interface AuditEvent {
  id: string; event_type: string; actor_type: string; actor_label: string | null; created_at: string
  details: Record<string, unknown>
}
export interface UploadReq { id: string; requested_items: RequestedItem[]; expires_at: string; revoked: boolean; remaining_uploads: number }
export interface ClaimDetail {
  claim: Claim; latest_evaluation: Evaluation | null; evidence: Evidence[]; claim_record_facts: Fact[]
  decisions: Decision[]; timeline: AuditEvent[]; upload_requests: UploadReq[]; synthetic_notice: string
}
export interface Policy {
  id: string; name: string; product_type: string; claim_type: string; covered_event_types: string[]
  excluded_event_types: string[]; note: string
}
