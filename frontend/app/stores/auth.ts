import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('agent_hub_token') || '',
    user: '',
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    async login(login: string, password: string) {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login, password }),
        credentials: 'include',
      })
      if (!res.ok) throw new Error('Invalid credentials')
      const data = await res.json()
      this.token = data.token
      this.user = data.user
      localStorage.setItem('agent_hub_token', data.token)
    },

    logout() {
      this.token = ''
      this.user = ''
      localStorage.removeItem('agent_hub_token')
      fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
    },
  },
})
