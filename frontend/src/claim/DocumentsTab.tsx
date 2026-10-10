import { useState } from 'react'
import { downloadUrl, fmtDate, label } from '../api'
import { ACCEPT, type DocSlot } from '../constants'
import { Badge } from '../components/ui'
import type { Evidence, Fact } from '../types'
import { pretty } from './format'

interface Props {
  claimId: string; slots: DocSlot[]; evidence: Evidence[]
  busyType: string | null; onUpload: (file: File, type: string) => void
}

const STATUS_TEXT: Record<string, string> = { SUCCEEDED: 'Read successfully', PARTIAL: 'Partly read', FAILED: 'Could not read', PENDING: 'Reading…' }

export default function DocumentsTab({ claimId, slots, evidence, busyType, onUpload }: Props) {
  return (
    <div>
      <p className="muted small hint-top">Upload photos, scans, PDFs or text files (up to 10 MB). Each upload is added as a new version, nothing is overwritten, and the claim is re-checked automatically.</p>
      <ul className="slots page-slots">
        {slots.map((s) => {
          const versions = evidence.filter((e) => e.evidence_type === s.type).sort((a, b) => b.version_number - a.version_number)
          const latest = versions[0]
          return (
            <li key={s.type} className={latest ? 'filled' : ''}>
              <div className="slot-main">
                <div className="slot-text">
                  <strong>{s.title}</strong> <span className={`tag ${s.required ? 'req' : ''}`}>{s.required ? 'Required' : 'Optional'}</span>
                  {!latest && <div className="muted small">{s.hint}</div>}
                </div>
                <label className={`btn small file-btn ${busyType === s.type ? 'disabled' : ''}`}>
                  {busyType === s.type ? 'Uploading…' : latest ? 'Upload new version' : 'Upload'}
                  <input type="file" accept={ACCEPT} hidden disabled={busyType !== null}
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f, s.type); e.target.value = '' }} />
                </label>
              </div>
              {latest && <EvidenceCard claimId={claimId} e={latest} older={versions.slice(1)} />}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function EvidenceCard({ claimId, e, older }: { claimId: string; e: Evidence; older: Evidence[] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="doc">
      <div className="doc-line">
        <span>📄 <a href={downloadUrl(claimId, e.id)} target="_blank" rel="noreferrer">{e.original_filename}</a> <span className="muted small">v{e.version_number} · {fmtDate(e.uploaded_at)}</span></span>
        <Badge value={e.extraction_status} text={STATUS_TEXT[e.extraction_status]} />
      </div>
      {e.extraction_status === 'FAILED' && <p className="muted small">We couldn't read text from this file. That doesn't mean the details are missing from the original; a clearer copy may help.</p>}
      {e.extraction_status === 'PARTIAL' && <p className="muted small">The file was read but none of the expected details were recognised.</p>}
      {e.facts.length > 0 && (
        <>
          <button className="link" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? '▾ Hide' : '▸ Show'} what we read ({e.facts.length})</button>
          {open && <FactList facts={e.facts} />}
        </>
      )}
      {older.length > 0 && <p className="muted small">Earlier versions kept: {older.map((o) => `v${o.version_number} (${o.original_filename})`).join(', ')}</p>}
    </div>
  )
}

export function FactList({ facts }: { facts: Fact[] }) {
  return (
    <dl className="facts-list">
      {facts.map((f) => {
        const low = f.confidence !== null && f.confidence < 0.8 && f.source !== 'CLAIM_RECORD'
        const p = pretty(f)
        return (
          <div key={f.id} className="fact-row">
            <dt>{label(f.field_name)}</dt>
            <dd>{p ?? <em className="muted">unclear: needs checking</em>}
              {f.source !== 'CLAIM_RECORD' && <span className={`muted small conf ${low ? 'low' : ''}`}> · {label(f.extraction_method).toLowerCase()}{f.confidence !== null ? `, ${Math.round(f.confidence * 100)}% sure` : ''}{low ? ' (low)' : ''}</span>}
              {f.source_snippet && f.source !== 'CLAIM_RECORD' && <div className="snippet small">“{f.source_snippet}”</div>}</dd>
          </div>
        )
      })}
    </dl>
  )
}
