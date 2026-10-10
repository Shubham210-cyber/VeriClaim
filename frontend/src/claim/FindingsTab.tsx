import { useState } from 'react'
import { downloadUrl, label } from '../api'
import { Badge } from '../components/ui'
import type { ClaimDetail, Evidence, Fact, Finding } from '../types'
import { friendly } from './pack'
import { pretty } from './format'

interface Props { detail: ClaimDetail; findings: Finding[]; facts: Map<string, Fact>; evidence: Map<string, Evidence>; claimId: string }

export default function FindingsTab({ detail, findings, facts, evidence, claimId }: Props) {
  // Plain wording for users: no internal codes, policy IDs, or the bracketed source notes (sources are shown as links).
  const clean = (s: string) => friendly(s, detail)
  const [tech, setTech] = useState(false)
  const [showOk, setShowOk] = useState(false)
  const visible = findings.filter((f) => f.result !== 'NOT_APPLICABLE' && f.rule_id !== 'SYS-002_AI_UNAVAILABLE')
  const issues = visible.filter((f) => ['FAIL', 'INDETERMINATE'].includes(f.result) && f.category !== 'NOTE')
  const notes = visible.filter((f) => f.category === 'NOTE' && f.result !== 'PASS')
  const passed = visible.filter((f) => !issues.includes(f) && !notes.includes(f))

  const sources = (f: Finding) => f.source_fact_ids.map((fid) => {
    const fact = facts.get(fid)
    if (!fact) return null
    const ev = fact.evidence_id ? evidence.get(fact.evidence_id) : null
    return (
      <li key={fid}><strong>{label(fact.field_name)}:</strong> {pretty(fact) ?? fact.raw_value}{' '}
        <span className="muted">{ev ? <>from <a href={downloadUrl(claimId, ev.id)} target="_blank" rel="noreferrer">{label(ev.evidence_type)}</a>{fact.source_page ? `, page ${fact.source_page}` : ''}</> : 'from the claim details'}</span></li>
    )
  })

  return (
    <div>
      <div className="tab-head">
        <p className="summary-line"><strong>{issues.length === 0 ? 'No issues found' : `${issues.length} thing${issues.length === 1 ? '' : 's'} to look at`}</strong>
          <span className="muted"> · {passed.length} check{passed.length === 1 ? '' : 's'} passed</span></p>
        <label className="check small"><input type="checkbox" checked={tech} onChange={(e) => setTech(e.target.checked)} /> Show technical details</label>
      </div>

      {issues.map((f) => (
        <article key={f.id} className={`finding ${f.result.toLowerCase()}`}>
          <header><h3>{f.title}</h3><Badge value={f.result} /></header>
          <p>{clean(f.explanation)}</p>
          {f.source_fact_ids.length > 0 ? <ul className="sources">{sources(f)}</ul> : <p className="muted small">Based on what is missing, so there is no document to link to.</p>}
          {f.recommended_action && <p className="next">💡 {f.recommended_action}</p>}
          {tech && <div className="rule">Rule {f.rule_id} · severity {f.severity.toLowerCase()}</div>}
        </article>
      ))}

      {notes.length > 0 && (
        <>
          <h4 className="sub">For your awareness</h4>
          {notes.map((f) => <article key={f.id} className="finding note-f"><header><h3>{f.title}</h3></header><p>{clean(f.explanation)}</p>{tech && <div className="rule">Rule {f.rule_id}</div>}</article>)}
        </>
      )}

      {passed.length > 0 && (
        <div className="passed">
          <button className="link" onClick={() => setShowOk(!showOk)} aria-expanded={showOk}>{showOk ? '▾' : '▸'} {passed.length} checks passed</button>
          {showOk && (
            <ul className="ok-list">
              {passed.map((f) => <li key={f.id}><span className="tick">✓</span><span><strong>{f.title}</strong><span className="muted small"> — {clean(f.explanation)}</span>{tech && <span className="rule inline-rule"> {f.rule_id}</span>}</span></li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
