import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, fmtDate, label } from '../api'
import { Empty, ErrorBox, Spinner } from '../components/ui'
import type { RequestedItem } from '../types'

interface Info { claim_reference: string; requested_items: RequestedItem[]; expires_at: string; remaining_uploads: number }

// Token-scoped page: shows only what the customer needs. No reviewer data is ever fetched here.
export default function CustomerUpload() {
  const { token = '' } = useParams()
  const headers = { 'X-Upload-Token': token }
  const [info, setInfo] = useState<Info | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [done, setDone] = useState<string[]>([])

  const load = useCallback(() => {
    api.get<Info>('/public/upload-request', headers).then((i) => { setInfo(i); setErr(null) }).catch((e: Error) => setErr(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])
  useEffect(load, [load])

  return (
    <div className="customer">
      <div className="brand center">VeriClaim</div>
      <h1>We need a few more documents</h1>
      {err && <ErrorBox message={err} />}
      {!err && !info && <Spinner />}
      {info && (
        <>
          <p className="muted">Claim <strong>{info.claim_reference}</strong>. Please upload the items below before {fmtDate(info.expires_at)}. You can upload up to {info.remaining_uploads} more file{info.remaining_uploads === 1 ? '' : 's'}.</p>
          {info.requested_items.length === 0 && <Empty>Nothing is currently requested.</Empty>}
          {info.requested_items.map((it, i) => (
            <Item key={i} item={it} token={token} disabled={info.remaining_uploads <= 0} done={done.includes(it.item_type + i)}
              onDone={() => { setDone([...done, it.item_type + i]); load() }} />
          ))}
          <p className="muted small">Accepted: PDF, PNG, JPEG or text files up to 10 MB. Demo environment: please use fake or sample documents only.</p>
        </>
      )}
    </div>
  )
}

function Item({ item, token, disabled, done, onDone }: { item: RequestedItem; token: string; disabled: boolean; done: boolean; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const send = async () => {
    if (!file) return
    setBusy(true); setErr(null)
    try { await api.upload('/public/upload-request/evidence', file, item.item_type, { 'X-Upload-Token': token }); onDone() } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <div className="panel">
      <strong>{label(item.item_type)}</strong>
      <p>{item.description}</p>
      {done ? <p className="ok">✓ Received. Thank you, a reviewer will take it from here.</p> : (
        <>
          <div className="row">
            <label className="btn file-btn" style={{ margin: 0 }}>{file ? 'Choose a different file' : 'Choose file'}
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" hidden onChange={(e) => setFile(e.target.files?.[0] ?? null)} aria-label={`File for ${label(item.item_type)}`} /></label>
            {file && <span className="file-name small">{file.name}</span>}
          </div>
          <div className="actions" style={{ marginTop: 14 }}>
            <button className="btn primary lg" disabled={!file || busy || disabled} onClick={send}>{busy ? 'Uploading…' : 'Send document'}</button>
          </div>
          {err && <ErrorBox message={err} />}
        </>
      )}
    </div>
  )
}
