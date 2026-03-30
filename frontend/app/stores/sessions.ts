import { defineStore } from 'pinia'

export interface SessionInfo {
  id: string
}

export const useSessionsStore = defineStore('sessions', {
  state: () => ({
    sessions: [] as SessionInfo[],
    activeId: null as string | null,
    loading: false,
  }),

  actions: {
    async fetch() {
      const api = useApi()
      try {
        const data = await api.get<{ sessions: SessionInfo[] }>('/api/sessions')
        this.sessions = data.sessions || []
      } catch { this.sessions = [] }
    },

    async create(sessionId: string, workdir: string, cli: string, resume: boolean = false) {
      const api = useApi()
      this.loading = true
      try {
        await api.post('/api/sessions', { session_id: sessionId, workdir, cli, resume })
        await this.fetch()
        this.setActive(sessionId)
      } finally { this.loading = false }
    },

    async remove(sessionId: string) {
      const api = useApi()
      await api.del(`/api/sessions/${sessionId}`)
      if (this.activeId === sessionId) this.activeId = null
      await this.fetch()
    },

    setActive(id: string | null) {
      this.activeId = id
      if (id) localStorage.setItem('ah_session', id)
      else localStorage.removeItem('ah_session')
    },

    restoreActive() {
      const saved = localStorage.getItem('ah_session')
      if (saved && this.sessions.find(s => s.id === saved)) {
        this.activeId = saved
      }
    },
  },
})
