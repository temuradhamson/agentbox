// WebSocket connects directly to backend, bypassing Nuxt dev proxy
export const WS_BASE = import.meta.dev
  ? 'ws://localhost:8924'
  : `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
