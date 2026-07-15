/**
 * API 客户端基础封装
 * 对接后端 FastAPI (localhost:18080)
 * 路径已对齐后端实际路由
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  signal?: AbortSignal
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}`
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...opts.headers }
  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.message || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Chat API ──
// 后端: POST /chat/messages, GET /chat/stream/{id}, POST /chat/stream/{id}/stop
export const chatApi = {
  async sendMessage(content: string, options?: { signal?: AbortSignal }): Promise<{ streamId: string }> {
    const res = await request<{ message_id: string }>('/chat/messages', {
      method: 'POST',
      body: { content },
      signal: options?.signal,
    })
    return { streamId: res.message_id }
  },
  connectStream(streamId: string, callbacks: {
    onToken?: (token: string) => void
    onToolCall?: (data: { name: string; args?: string }) => void
    onToolResult?: (index: number) => void
    onDone?: () => void
    onError?: (e: Error) => void
  }): EventSource {
    const es = new EventSource(`${API_BASE}/chat/stream/${streamId}`)
    es.addEventListener('token', (e) => { try { const d = JSON.parse(e.data); callbacks.onToken?.(d.token || '') } catch {} })
    es.addEventListener('tool_call', (e) => { try { callbacks.onToolCall?.(JSON.parse(e.data)) } catch {} })
    es.addEventListener('tool_result', (e) => { try { const d = JSON.parse(e.data); callbacks.onToolResult?.(d.index || 0) } catch {} })
    es.addEventListener('done', () => { callbacks.onDone?.(); es.close() })
    es.addEventListener('error', () => { if (es.readyState === EventSource.CLOSED) callbacks.onError?.(new Error('连接已关闭')) })
    return es
  },
  stopStream(streamId: string) { return request(`/chat/stream/${streamId}/stop`, { method: 'POST' }) },
}

// ── Projects API → 后端 Workspaces ──
// 后端: GET /workspaces, POST /workspaces, GET /workspaces/{id}, PUT /workspaces/{id}
export const projectApi = {
  list() { return request<Array<{ id: string; name: string; created_at: string }>>('/workspaces') },
  get(id: string) { return request(`/workspaces/${id}`) },
  create(data: { name: string; description?: string }) { return request('/workspaces', { method: 'POST', body: data }) },
  remove(id: string) { return request(`/workspaces/${id}`, { method: 'DELETE' }) },
}

// ── Memory API ──
// 后端: GET /memory/context, GET /memory/search?q=
export const memoryApi = {
  search(query: string) { return request(`/memory/search?q=${encodeURIComponent(query)}`) },
  list(type?: string) { return request(`/memory/context${type ? '?type=' + type : ''}`) },
}

// ── Plaza API ──
// 后端: GET /skills/market, GET /experts, GET /models/marketplace
export const plazaApi = {
  skills() { return request<Array<{ id: string; name: string; desc: string; downloads: number }>>('/skills/market') },
  experts() { return request('/experts') },
  models() { return request('/models/marketplace') },
}

// ── Files API ──
// 后端: GET /files, POST /files/upload
export const fileApi = {
  list() { return request('/files') },
  upload(formData: FormData) {
    return fetch(`${API_BASE}/files/upload`, { method: 'POST', body: formData }).then(r => r.json())
  },
}

// ── Connections API ──
// 后端: GET /connections, GET /connections/{id}/health
export const connectionApi = {
  list() { return request('/connections') },
  health(id: string) { return request(`/connections/${id}/health`) },
}

// ── Settings API ──
// 后端: GET /settings, PUT /settings, GET /api-keys/status, POST /api-keys/configure
export const settingsApi = {
  get() { return request('/settings') },
  update(data: Record<string, unknown>) { return request('/settings', { method: 'PUT', body: data }) },
  apiKeys() { return request('/api-keys/status') },
  addApiKey(provider: string, key: string) { return request('/api-keys/configure', { method: 'POST', body: { provider, api_key: key } }) },
}
