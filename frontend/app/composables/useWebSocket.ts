import { ref, onUnmounted } from 'vue'

export function useWebSocket(urlFactory: () => string) {
  const connected = ref(false)
  const data = ref<any>(null)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let intentionalClose = false

  function connect() {
    if (ws) return
    intentionalClose = false
    const url = urlFactory()
    ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      connected.value = true
      reconnectDelay = 1000
    }

    ws.onmessage = (e) => {
      data.value = e.data
    }

    ws.onclose = () => {
      connected.value = false
      ws = null
      if (!intentionalClose) {
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, 30000)
          connect()
        }, reconnectDelay)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function send(msg: string | ArrayBuffer) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(msg)
    }
  }

  function close() {
    intentionalClose = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
    ws = null
    connected.value = false
  }

  onUnmounted(close)

  return { connected, data, connect, send, close }
}
