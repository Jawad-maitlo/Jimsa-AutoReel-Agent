const API_ROOT = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || '/api'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_ROOT}${path}`, options)
  } catch {
    throw new ApiError('Cannot reach the local API. Start it with start_windows.bat, then retry.', 0)
  }
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('json') ? await response.json() : await response.text()
  if (!response.ok) {
    const detail = typeof body === 'object' && body && 'detail' in body ? body.detail : body
    throw new ApiError(typeof detail === 'string' ? detail : `Request failed (${response.status})`, response.status)
  }
  return body as T
}

export function json(method: 'POST' | 'PATCH' | 'DELETE', body?: unknown): RequestInit {
  return { method, ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) }
}

export function mediaUrl(path: string | null): string {
  if (!path) return ''
  return `${API_ROOT.replace(/\/api$/, '')}${path}`
}

export function uploadVideo(projectId: number, file: File): RequestInit {
  const data = new FormData()
  data.append('project_id', String(projectId))
  data.append('file', file)
  return { method: 'POST', body: data }
}

export { API_ROOT }
