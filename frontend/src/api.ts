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
    throw new ApiError(0, 'NETWORK', 'Cannot reach the server. Is the backend running on port 8000?')
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const e = body?.error
    throw new ApiError(res.status, e?.code ?? 'ERROR', e?.message ?? `Request failed (${res.status})`)
  }
  return body as T
}

const json = (method: string, data?: unknown, headers: Record<string, string> = {}): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json', ...headers },
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
export const label = (s: string | null | undefined) => (s ?? '—').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase())
export const fmtDate = (s: string | null | undefined) => (s ? new Date(s).toLocaleString() : '—')
