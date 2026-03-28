export function useApi() {
  const authStore = useAuthStore()

  async function request<T = any>(url: string, opts: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = { ...opts.headers as Record<string, string> }
    if (authStore.token) {
      headers['Authorization'] = `Bearer ${authStore.token}`
    }
    if (!headers['Content-Type'] && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(url, { ...opts, headers, credentials: 'include' })
    if (res.status === 401) {
      authStore.logout()
      navigateTo('/login')
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    return res.json()
  }

  return {
    get: <T = any>(url: string) => request<T>(url),
    post: <T = any>(url: string, body?: any) => request<T>(url, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
    del: <T = any>(url: string) => request<T>(url, { method: 'DELETE' }),
  }
}
