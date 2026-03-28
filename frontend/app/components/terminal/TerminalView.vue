<script setup lang="ts">
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

const props = defineProps<{ sessionId: string }>()
const auth = useAuthStore()

const termRef = ref<HTMLElement>()
let term: Terminal | null = null
let fitAddon: FitAddon | null = null

import { WS_BASE } from '~/utils/constants'

const ws = useWebSocket(() => `${WS_BASE}/ws/terminal/${props.sessionId}?token=${auth.token}`)

watch(() => ws.data.value, (raw) => {
  if (!raw || !term) return
  if (raw instanceof ArrayBuffer) term.write(new Uint8Array(raw))
  else term.write(raw)
})

watch(() => ws.connected.value, (c) => {
  if (c && term && fitAddon) {
    term.reset()
    fitAddon.fit()
    ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    term.focus()
  }
})

onMounted(() => {
  if (!termRef.value) return
  term = new Terminal({
    theme: {
      background: '#08090c', foreground: '#e2e8f0', cursor: '#d4a574', cursorAccent: '#08090c',
      selectionBackground: '#d4a57430',
      black: '#3d405a', red: '#f87171', green: '#34d399', yellow: '#fbbf24',
      blue: '#60a5fa', magenta: '#c084fc', cyan: '#22d3ee', white: '#cbd5e1',
      brightBlack: '#64748b', brightRed: '#fca5a5', brightGreen: '#6ee7b7', brightYellow: '#fde68a',
      brightBlue: '#93c5fd', brightMagenta: '#d8b4fe', brightCyan: '#67e8f9', brightWhite: '#f1f5f9',
    },
    fontFamily: "'JetBrains Mono','Fira Code','Cascadia Code','Consolas',monospace",
    fontSize: 14, lineHeight: 1.4, cursorBlink: true, cursorStyle: 'bar', scrollback: 10000,
  })
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.loadAddon(new WebLinksAddon())
  term.open(termRef.value)
  fitAddon.fit()

  new ResizeObserver(() => fitAddon?.fit()).observe(termRef.value)
  term.onResize(({ cols, rows }) => ws.send(JSON.stringify({ type: 'resize', cols, rows })))
  term.onData((data) => ws.send(data))

  ws.connect()
})

onUnmounted(() => {
  ws.close()
  term?.dispose()
})
</script>

<template>
  <div class="h-full w-full">
    <div ref="termRef" class="h-full w-full" />
  </div>
</template>

<style>
.xterm-viewport::-webkit-scrollbar { width: 0; display: none; }
.xterm-viewport { scrollbar-width: none; }
</style>
