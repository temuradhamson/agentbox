<script setup lang="ts">
import { WS_BASE } from '~/utils/constants'
import { formatRelativeDate, formatTime, formatDayHeader, isDifferentDay } from '~/utils/time'

definePageMeta({ middleware: 'auth' })

const auth = useAuthStore()
const sessions = useSessionsStore()
const chat = useChatStore()

// Scroll-to-bottom button
const chatScroll = ref<HTMLElement | null>(null)
const showScrollBtn = ref(false)

function onChatScroll() {
  const el = chatScroll.value
  if (!el) return
  showScrollBtn.value = el.scrollHeight - el.scrollTop - el.clientHeight > el.clientHeight
}

function scrollToBottom(smooth = true) {
  const el = chatScroll.value
  if (!el) return
  el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'instant' })
}

// Swipe to open sidebar (mobile)
let touchStartX = 0
let touchStartY = 0
let swiping = false

function onTouchStart(e: TouchEvent) {
  const x = e.touches[0].clientX
  // Ignore touches from the very left 20px (iOS back gesture zone)
  if (x < 20) return
  touchStartX = x
  touchStartY = e.touches[0].clientY
  swiping = true
}

function onTouchEnd(e: TouchEvent) {
  if (!swiping) return
  swiping = false
  const dx = e.changedTouches[0].clientX - touchStartX
  const dy = Math.abs(e.changedTouches[0].clientY - touchStartY)
  // Horizontal swipe > 60px, more horizontal than vertical
  if (dx > 60 && dx > dy) {
    sidebarOpen.value = true
  }
  // Swipe left to close sidebar
  if (dx < -60 && -dx > dy && sidebarOpen.value) {
    sidebarOpen.value = false
  }
}
const mode = ref<'chat' | 'terminal'>((localStorage.getItem('ah_mode') as any) || 'chat')
const sidebarOpen = ref(localStorage.getItem('ah_sidebar') !== 'false')
const autoTts = ref(localStorage.getItem('ah_autotts') !== 'false')

watch(mode, (v) => {
  localStorage.setItem('ah_mode', v)
  // When switching modes, mark current audio as played so they don't replay
  markExistingAudio(chat.messages)
})
watch(sidebarOpen, (v) => localStorage.setItem('ah_sidebar', String(v)))
watch(autoTts, (v) => localStorage.setItem('ah_autotts', String(v)))

// TTS WebSocket — connects directly to Agent Box (like port 8921 does)
const abToken = ref('')
const ttsWs = useWebSocket(() => {
  const base = 'ws://localhost:8922'
  return `${base}/ws/tts?token=${abToken.value}`
})

// TTS audio queue (with preload, matching 8921 implementation)
const audioQueue: string[] = []
let currentAudio: HTMLAudioElement | null = null
let nextAudio: HTMLAudioElement | null = null
let playLock = false
const QUEUE_MAX = 30
const ttsPlaying = ref(false)

function preloadNext() {
  if (nextAudio || !audioQueue.length) return
  nextAudio = new Audio(audioQueue[0])
  nextAudio.preload = 'auto'
}

function playNext() {
  if (playLock || currentAudio) return
  if (!audioQueue.length) { ttsPlaying.value = false; nextAudio = null; return }
  playLock = true
  const url = audioQueue.shift()!
  // Use preloaded audio if URL matches
  if (nextAudio && nextAudio.src.endsWith(new URL(url, location.href).pathname)) {
    currentAudio = nextAudio
  } else {
    currentAudio = new Audio(url)
  }
  nextAudio = null
  ttsPlaying.value = true

  const advance = () => {
    if (!currentAudio) return
    currentAudio.onended = null
    currentAudio.onerror = null
    currentAudio = null
    playLock = false
    preloadNext()
    playNext()
  }
  currentAudio.onended = advance
  currentAudio.onerror = () => { nextAudio = null; advance() }
  currentAudio.play().then(() => { playLock = false }).catch(() => { nextAudio = null; advance() })
  preloadNext()
}

function stopAudio() {
  audioQueue.length = 0
  nextAudio = null
  playLock = false
  if (currentAudio) { currentAudio.onended = null; currentAudio.onerror = null; currentAudio.pause(); currentAudio = null }
  ttsPlaying.value = false
}

function hasAudioUrl(content: string) {
  if (!content) return false
  // Collapse newlines first — terminal wraps URLs across lines
  const flat = content.replace(/\n/g, '')
  return /\.wav/i.test(flat) && /https?:\/\//i.test(flat)
}

function extractAudioUrl(content: string): string {
  if (!content) return ''
  const flat = content.replace(/\n/g, '')
  // Try JSON: {"result": "https://...wav"}
  try {
    const obj = JSON.parse(flat)
    if (obj.result && /\.wav/i.test(obj.result)) return obj.result
  } catch {}
  // Fallback: regex
  const m = flat.match(/https?:\/\/[^\s"'}\]]+\.wav/i)
  return m ? m[0] : ''
}

// Bar count: ~3px per bar (2px bar + 1px gap), based on max-w-md (448px) minus button (52px) = ~396px
const barCount = 130

function extractTtsText(content: string): string {
  // Extract text from: tts - tts (MCP)(text: "...", voice: ...)
  const m = content.match(/text:\s*"([^"]*(?:"[^"]*)*?)"/s)
  if (m) return m[1].replace(/\\n/g, '\n').replace(/\\"/g, '"')
  // Fallback: content after first (
  const p = content.indexOf('(text:')
  if (p >= 0) return content.slice(p + 6).replace(/[",)]+$/, '').trim()
  return content
}

function playUrl(url: string) {
  if (!url) return
  stopAudio()
  audioQueue.push(url)
  playNext()
}

// ── Per-message audio players (Telegram-style) ──
const audioPlayers = reactive<Record<number, {
  audio: HTMLAudioElement | null
  playing: boolean
  progress: number
  currentTime: number
  duration: number
  waveform: number[]
}>>({})

function getPlayer(idx: number, url: string) {
  if (!audioPlayers[idx]) {
    // Generate pseudo-random waveform from URL hash
    const wave: number[] = []
    let hash = 0
    for (let c = 0; c < url.length; c++) hash = ((hash << 5) - hash + url.charCodeAt(c)) | 0
    for (let b = 0; b < 130; b++) {
      hash = ((hash << 5) - hash + b * 7) | 0
      wave.push(6 + Math.abs(hash % 18))
    }
    audioPlayers[idx] = { audio: null, playing: false, progress: 0, currentTime: 0, duration: 0, waveform: wave }
  }
  return audioPlayers[idx]
}

function toggleAudioMsg(idx: number, url: string) {
  const p = getPlayer(idx, url)
  if (p.playing && p.audio) {
    p.audio.pause()
    p.playing = false
    return
  }
  // Pause any other playing message
  for (const k of Object.keys(audioPlayers)) {
    const other = audioPlayers[+k]
    if (other.playing && other.audio) { other.audio.pause(); other.playing = false }
  }
  if (!p.audio) {
    p.audio = new Audio(url)
    p.audio.addEventListener('loadedmetadata', () => { p.duration = p.audio!.duration })
    p.audio.addEventListener('timeupdate', () => {
      p.currentTime = p.audio!.currentTime
      p.progress = p.duration > 0 ? p.currentTime / p.duration : 0
    })
    p.audio.addEventListener('ended', () => { p.playing = false; p.progress = 0; p.currentTime = 0 })
    p.audio.addEventListener('error', () => { p.playing = false })
  }
  p.audio.play().catch(() => { p.playing = false })
  p.playing = true
}

function seekAudioMsg(idx: number, e: MouseEvent) {
  const p = audioPlayers[idx]
  if (!p?.audio || !p.duration) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  p.audio.currentTime = ratio * p.duration
  if (!p.playing) { p.audio.play().catch(() => {}); p.playing = true }
}

function waveformHeight(idx: number, bar: number, url?: string): number {
  if (url && !audioPlayers[idx]) getPlayer(idx, url)
  const p = audioPlayers[idx]
  return p?.waveform?.[bar - 1] ?? 8
}

const _preloaded = new Set<number>()
function preloadAudioDuration(idx: number, url: string) {
  if (_preloaded.has(idx) || !url) return
  _preloaded.add(idx)
  const p = getPlayer(idx, url)
  if (p.duration > 0) return
  const a = new Audio()
  a.preload = 'metadata'
  a.src = url
  a.addEventListener('loadedmetadata', () => {
    p.duration = a.duration
  }, { once: true })
}

function formatDuration(sec: number): string {
  if (!sec || !isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

watch(() => ttsWs.data.value, (raw) => {
  if (!raw || typeof raw !== 'string') return
  if (!autoTts.value) return
  try {
    const d = JSON.parse(raw)
    if (!d.url) return
    if (audioQueue.length >= QUEUE_MAX) return
    audioQueue.push(d.url)
    if (!currentAudio) playNext(); else preloadNext()
  } catch {}
})

// Load messages from Agent Box (parsed server-side)
let pollTimer: ReturnType<typeof setInterval> | null = null

const _playedAudioUrls = new Set<string>()
let _initialLoad = true

async function loadMessages(id: string) {
  if (sessions.activeId !== id) return
  try {
    const api = useApi()
    const data = await api.get<{ messages: any[] }>(`/api/sessions/${id}/messages`)
    if (sessions.activeId !== id) return
    if (!data.messages) return

    const newJson = JSON.stringify(data.messages)
    const changed = newJson !== JSON.stringify(chat.messages)
    if (!changed) return

    // Autoplay: scan ALL messages for new audio URLs not yet played (skip initial load)
    if (autoTts.value && !_initialLoad) {
      let queued = false
      for (const msg of data.messages) {
        if (msg.type === 'tool_result' && hasAudioUrl(msg.content)) {
          const url = extractAudioUrl(msg.content)
          if (url && !_playedAudioUrls.has(url)) {
            _playedAudioUrls.add(url)
            audioQueue.push(url)
            queued = true
          }
        }
      }
      if (queued) {
        if (!currentAudio) playNext(); else preloadNext()
      }
    }

    chat.setMessages(data.messages)
    // Auto-scroll to bottom on new messages (only if already near bottom)
    await nextTick()
    const el = chatScroll.value
    if (el) {
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < el.clientHeight
      if (nearBottom || _initialLoad) {
        el.scrollTo({ top: el.scrollHeight, behavior: 'instant' })
      }
    }
  } catch {}
}

// Mark all existing audio as "already played" on initial load
function markExistingAudio(msgs: any[]) {
  for (const msg of msgs) {
    if (msg.type === 'tool_result' && hasAudioUrl(msg.content)) {
      const url = extractAudioUrl(msg.content)
      if (url) _playedAudioUrls.add(url)
    }
  }
}

watch(() => sessions.activeId, async (id, oldId) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (id === oldId) return
  _playedAudioUrls.clear()
  chat.clear()
  if (!id) return
  chat.sessionId = id
  _initialLoad = true
  await loadMessages(id)
  markExistingAudio(chat.messages)
  _initialLoad = false
  await nextTick()
  scrollToBottom(false)
  pollTimer = setInterval(() => loadMessages(id), 3000)
})

onMounted(async () => {
  await sessions.fetch()
  // Get Agent Box token for direct TTS WS connection
  try {
    const api = useApi()
    const data = await api.get<{ token: string }>('/api/auth/agent-box-token')
    abToken.value = data.token
    ttsWs.connect()
  } catch { console.warn('Could not get Agent Box token for TTS') }
  // Restore last active session, or pick first
  sessions.restoreActive()
  if (sessions.sessions.length && !sessions.activeId) {
    sessions.setActive(sessions.sessions[0].id)
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  ttsWs.close()
  stopAudio()
})

onUnmounted(() => {
  chatWs.close()
  ttsWs.close()
  stopAudio()
})

// New session dialog
const showNewSession = ref(false)
const newId = ref('')
const newCli = ref('claude')

function confirmDelete(id: string) {
  if (confirm(`Delete session "${id}"?`)) {
    sessions.remove(id)
  }
}

function selectSession(id: string) {
  sessions.setActive(id)
  if (window.innerWidth < 768) sidebarOpen.value = false
}

async function createSession() {
  if (!newId.value) return
  try {
    await sessions.create(newId.value, '/workspace', newCli.value)
    showNewSession.value = false
    newId.value = ''
  } catch (e: any) {
    console.error('Create session failed:', e)
    alert('Failed to create session: ' + (e.message || e))
  }
}
</script>

<template>
  <div class="h-[100dvh] flex bg-surface-950 overflow-hidden" @touchstart="onTouchStart" @touchend="onTouchEnd">
    <!-- Mobile overlay backdrop -->
    <transition name="fade">
      <div v-if="sidebarOpen" class="md:hidden fixed inset-0 bg-black/50 z-40" @click="sidebarOpen = false" />
    </transition>

    <!-- Sidebar: overlay on mobile, inline on desktop -->
    <aside :class="[
        'bg-surface-900 border-r border-surface-700 flex flex-col transition-all duration-200 overflow-hidden',
        'max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:shadow-2xl',
        'md:flex-shrink-0',
        sidebarOpen ? 'w-72' : 'w-0 border-r-0'
      ]">
      <div class="w-72 h-full flex flex-col">
        <!-- Header -->
        <div class="p-4 border-b border-surface-700">
          <div class="flex items-center justify-between mb-3">
            <h1 class="text-sm font-bold text-white flex items-center gap-2">
              🤖 Agent Hub
            </h1>
            <button @click="sidebarOpen = false" title="Скрыть меню"
              class="w-7 h-7 rounded-lg bg-surface-800 border border-surface-600 hover:bg-surface-700 text-surface-500 hover:text-white flex items-center justify-center transition text-sm">
              &lt;
            </button>
          </div>
          <button @click="showNewSession = true"
            class="w-full h-9 rounded-lg text-sm font-medium text-white bg-accent hover:bg-accent-hover transition shadow-[0_0_12px_var(--color-accent-glow)]">
            + New Session
          </button>
        </div>

        <!-- Sessions list -->
        <div class="flex-1 overflow-y-auto p-2 space-y-1">
          <div v-for="s in sessions.sessions" :key="s.id"
            @click="selectSession(s.id)"
            :class="[
              'group px-3 py-2.5 rounded-lg cursor-pointer transition-all text-sm',
              sessions.activeId === s.id
                ? 'bg-accent/10 border border-accent/30 text-white'
                : 'hover:bg-surface-800 text-surface-500 hover:text-white border border-transparent'
            ]">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <span class="w-2 h-2 rounded-full bg-ok flex-shrink-0" />
                <span class="truncate font-medium">{{ s.id }}</span>
              </div>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <span class="text-[10px] text-surface-600">{{ formatRelativeDate(s.last_active) }}</span>
                <button @click.stop="confirmDelete(s.id)"
                  class="w-5 h-5 rounded flex items-center justify-center text-surface-600 hover:text-danger hover:bg-danger/10 transition opacity-0 group-hover:opacity-100"
                  title="Delete session">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          <p v-if="!sessions.sessions.length" class="text-center text-surface-600 text-xs py-8">
            No active sessions
          </p>
        </div>
        <!-- Logout at bottom -->
        <div class="p-3 border-t border-surface-700">
          <button @click="auth.logout(); navigateTo('/login')"
            class="w-full h-8 rounded-lg text-xs text-surface-500 hover:text-white hover:bg-surface-800 transition flex items-center justify-center gap-1.5">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Logout
          </button>
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- Top bar -->
      <div class="h-12 border-b border-surface-700 bg-surface-900 flex items-center justify-between px-4 flex-shrink-0">
        <div class="flex items-center gap-2">
          <button @click="sidebarOpen = true"
            class="w-8 h-8 rounded-lg bg-surface-800 border border-surface-600 hover:bg-surface-700 text-surface-500 hover:text-white flex items-center justify-center transition text-sm"
            :class="sidebarOpen ? 'max-md:block hidden' : ''">
            ☰
          </button>
          <span class="text-sm font-medium text-white">{{ sessions.activeId || 'Select a session' }}</span>
          <span v-if="sessions.activeId" class="w-2 h-2 rounded-full bg-ok" />
        </div>
        <div v-if="sessions.activeId" class="flex items-center gap-1">
          <button @click="mode = 'chat'"
            :class="['px-3 py-1 rounded-md text-xs font-medium transition flex items-center gap-1', mode === 'chat' ? 'bg-accent text-white' : 'text-surface-500 hover:text-white']">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span class="max-md:hidden">Chat</span>
          </button>
          <button @click="mode = 'terminal'"
            :class="['px-3 py-1 rounded-md text-xs font-medium transition flex items-center gap-1', mode === 'terminal' ? 'bg-accent text-white' : 'text-surface-500 hover:text-white']">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
            </svg>
            <span class="max-md:hidden">Terminal</span>
          </button>
          <button @click="autoTts = !autoTts"
            :class="['px-3 py-1 rounded-md text-xs font-medium transition flex items-center gap-1',
              autoTts ? 'bg-ok/15 text-ok' : 'text-surface-500 hover:text-white']"
            :title="autoTts ? 'Автоозвучка включена' : 'Автоозвучка выключена'">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon v-if="autoTts" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <path v-if="autoTts" d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
              <path v-if="autoTts" d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
              <polygon v-if="!autoTts" points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
              <line v-if="!autoTts" x1="23" y1="9" x2="17" y2="15"/>
              <line v-if="!autoTts" x1="17" y1="9" x2="23" y2="15"/>
            </svg>
            <span class="max-md:hidden">{{ autoTts ? 'Auto' : 'Mute' }}</span>
          </button>
        </div>
      </div>

      <!-- Chat / Terminal view -->
      <div class="flex-1 overflow-hidden relative">
        <!-- Empty state -->
        <div v-if="!sessions.activeId" class="h-full flex items-center justify-center">
          <div class="text-center">
            <div class="text-5xl mb-4 opacity-30">🤖</div>
            <p class="text-surface-500">Select or create a session</p>
          </div>
        </div>

        <!-- Chat mode -->
        <div v-else-if="mode === 'chat'" class="h-full flex flex-col relative">
          <div ref="chatScroll" @scroll="onChatScroll" class="flex-1 overflow-y-auto p-4 space-y-3 relative">
            <template v-for="(msg, i) in chat.messages" :key="i">
              <!-- Day separator (only for messages with real timestamps) -->
              <div v-if="msg.timestamp && (i === 0 || !chat.messages[i-1]?.timestamp || isDifferentDay(chat.messages[i-1].timestamp, msg.timestamp))"
                class="flex justify-center my-4">
                <span class="px-3 py-1 rounded-full bg-surface-800 border border-surface-700 text-[11px] text-surface-500">
                  {{ formatDayHeader(msg.timestamp) }}
                </span>
              </div>

              <div :class="['max-w-3xl max-md:max-w-full min-w-0 break-words overflow-hidden', msg.role === 'user' ? 'ml-auto' : '']">
              <!-- User message -->
              <div v-if="msg.role === 'user' && msg.type === 'text'"
                class="bg-accent/10 border border-accent/20 rounded-xl px-4 py-2.5 text-sm text-white">
                <div>{{ msg.content }}</div>
                <div v-if="msg.timestamp" class="text-[10px] text-accent/50 text-right mt-1">{{ formatTime(msg.timestamp) }}</div>
              </div>

              <!-- Assistant text -->
              <div v-else-if="msg.role === 'assistant' && msg.type === 'text'"
                class="bg-surface-800 border border-surface-700 rounded-xl px-4 py-2.5 text-sm prose overflow-hidden">
                <div v-html="msg.content" />
                <div v-if="msg.timestamp" class="text-[10px] text-surface-600 text-right mt-1">{{ formatTime(msg.timestamp) }}</div>
              </div>

              <!-- TTS tool use — show the spoken text -->
              <div v-else-if="msg.type === 'tool_use' && msg.tool_name === 'tts'"
                class="bg-surface-800/50 border border-surface-700 rounded-xl px-4 py-2.5 text-sm text-surface-400 italic">
                <div class="flex items-center gap-1.5 text-[10px] text-surface-600 mb-1">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
                  TTS
                </div>
                {{ extractTtsText(msg.content) }}
                <div v-if="msg.timestamp" class="text-[10px] text-surface-600 text-right mt-1">{{ formatTime(msg.timestamp) }}</div>
              </div>

              <!-- Other tool use -->
              <details v-else-if="msg.type === 'tool_use'"
                class="bg-surface-800/50 border border-surface-700 rounded-lg text-xs min-w-0">
                <summary class="px-3 py-2 cursor-pointer text-surface-500 hover:text-white transition">
                  🔧 {{ msg.tool_name }}
                </summary>
                <pre class="px-3 py-2 overflow-x-auto text-surface-500 border-t border-surface-700">{{ msg.content }}</pre>
              </details>

              <!-- Audio player (Telegram-style voice message) -->
              <div v-else-if="msg.type === 'tool_result' && hasAudioUrl(msg.content)"
                class="bg-surface-800 border border-surface-700 rounded-2xl px-3 py-2 w-full max-w-md"
                :ref="(el: any) => preloadAudioDuration(i, extractAudioUrl(msg.content))">
                <div class="flex items-center gap-3">
                  <button @click="toggleAudioMsg(i, extractAudioUrl(msg.content))"
                    class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition"
                    :class="audioPlayers[i]?.playing ? 'bg-accent text-white' : 'bg-accent/20 text-accent hover:bg-accent/30'">
                    <span v-if="audioPlayers[i]?.playing" class="text-sm">⏸</span>
                    <span v-else class="text-sm ml-0.5">▶</span>
                  </button>
                  <div class="flex-1 min-w-0">
                    <div class="relative h-8 flex items-center cursor-pointer group"
                      @click="seekAudioMsg(i, $event)">
                      <div class="flex items-end w-full h-6 overflow-hidden" style="gap:1px;">
                        <div v-for="b in barCount" :key="b"
                          class="flex-1 rounded-sm transition-colors" style="max-width:2px;min-width:1px;"
                          :class="audioPlayers[i] && (b / barCount) <= (audioPlayers[i].progress || 0) ? 'bg-accent' : 'bg-surface-600 group-hover:bg-surface-500'"
                          :style="{ height: waveformHeight(i, b, extractAudioUrl(msg.content)) + 'px' }" />
                      </div>
                    </div>
                    <div class="flex justify-between text-[10px] text-surface-500 mt-0.5 px-0.5">
                      <span>{{ formatDuration(audioPlayers[i]?.currentTime || 0) }}</span>
                      <span>{{ formatDuration(audioPlayers[i]?.duration || 0) }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="msg.timestamp" class="text-[10px] text-surface-600 text-right mt-1">{{ formatTime(msg.timestamp) }}</div>
              </div>

              <!-- Tool result (non-audio) -->
              <details v-else-if="msg.type === 'tool_result'"
                class="bg-surface-800/50 border border-surface-700 rounded-lg text-xs min-w-0">
                <summary :class="['px-3 py-2 cursor-pointer transition', msg.is_error ? 'text-danger' : 'text-surface-500 hover:text-white']">
                  {{ msg.is_error ? '❌' : '✅' }} Result
                </summary>
                <pre class="px-3 py-2 overflow-x-auto text-surface-500 border-t border-surface-700">{{ msg.content }}</pre>
              </details>

              <!-- Thinking -->
              <details v-else-if="msg.type === 'thinking'"
                class="bg-surface-800/30 border border-surface-700/50 rounded-lg text-xs">
                <summary class="px-3 py-2 cursor-pointer text-surface-600">💭 Thinking...</summary>
                <div class="px-3 py-2 text-surface-600 border-t border-surface-700/50">{{ msg.content }}</div>
              </details>
              </div>
            </template>
          </div>

          <!-- Scroll to bottom -->
          <transition name="fade">
            <button v-if="showScrollBtn" @click="scrollToBottom"
              class="absolute bottom-20 left-1/2 -translate-x-1/2 z-10 w-10 h-10 rounded-full bg-surface-700 border border-surface-600 text-surface-300 hover:bg-surface-600 hover:text-white flex items-center justify-center shadow-lg transition">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
          </transition>

          <!-- Input bar -->
          <div class="border-t border-surface-700 bg-surface-900 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] flex items-center gap-3 flex-shrink-0">
            <!-- Stop TTS -->
            <button @click="stopAudio()" v-if="ttsPlaying"
              class="w-9 h-9 rounded-full bg-ok/10 border border-ok/30 text-ok flex items-center justify-center text-sm flex-shrink-0">
              🔊
            </button>
            <!-- Mic button -->
            <button @click="toggleMic()"
              :class="[
                'w-10 h-10 rounded-full flex items-center justify-center transition flex-shrink-0 border relative',
                isRecording
                  ? 'bg-danger border-danger/50 text-white'
                  : 'bg-surface-800 border-surface-600 hover:border-accent/50 hover:bg-surface-700 text-surface-500 hover:text-accent'
              ]"
              :title="isRecording ? 'Остановить запись' : 'Голосовой ввод'">
              <!-- Pulse ring when recording -->
              <span v-if="isRecording" class="absolute inset-0 rounded-full border-2 border-danger animate-ping opacity-40" />
              <!-- Level ring -->
              <svg v-if="isRecording" class="absolute inset-0 w-full h-full" viewBox="0 0 40 40">
                <circle cx="20" cy="20" :r="16" fill="none" stroke="white" stroke-opacity="0.3" stroke-width="2"
                  :stroke-dasharray="`${micLevel * 100} 100`" stroke-linecap="round"
                  transform="rotate(-90 20 20)" />
              </svg>
              <svg v-if="!isRecording" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="1" width="6" height="12" rx="3"/>
                <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
              <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
              </svg>
            </button>
            <!-- Recording visualizer or status -->
            <div v-if="isRecording" class="flex-1 flex items-center gap-2">
              <div class="flex items-end gap-px h-6 flex-1">
                <div v-for="b in 30" :key="b" class="flex-1 rounded-sm bg-danger/60 transition-all duration-75"
                  :style="{ height: micBars[b - 1] + 'px' }" />
              </div>
              <span class="text-xs text-danger font-mono flex-shrink-0">{{ recordingTime }}</span>
            </div>
            <div v-else-if="micStatus" class="flex-1 text-sm text-surface-500 truncate">
              {{ micStatus }}
            </div>
            <input v-else v-model="inputText" @keydown.enter="sendMessage" placeholder="Send a message..."
              class="focus-ring flex-1 bg-surface-800 border border-surface-600 rounded-lg px-4 py-2.5 text-sm text-white placeholder-surface-600 transition hover:border-surface-500" />
            <button v-if="!isRecording" @click="sendMessage"
              class="h-10 px-5 rounded-lg text-sm font-medium text-white bg-accent hover:bg-accent-hover transition flex-shrink-0">
              Send
            </button>
          </div>
        </div>

        <!-- Terminal mode -->
        <div v-else-if="mode === 'terminal'" class="h-full flex flex-col">
          <div class="flex-1 overflow-hidden">
            <ClientOnly>
              <LazyTerminalView :key="sessions.activeId" :session-id="sessions.activeId!" />
            </ClientOnly>
          </div>
          <!-- Terminal toolbar -->
          <div class="border-t border-surface-700 bg-surface-900 px-3 py-2 flex items-center gap-2 flex-shrink-0">
            <button @click="sendTermKey('\x03')" title="Ctrl+C"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              Ctrl+C
            </button>
            <button @click="sendTermKey('\x04')" title="Ctrl+D"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              Ctrl+D
            </button>
            <button @click="sendTermKey('\x1a')" title="Ctrl+Z"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              Ctrl+Z
            </button>
            <button @click="sendTermKey('\x1b')" title="Escape"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              Esc
            </button>
            <button @click="sendTermKey('\t')" title="Tab"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              Tab
            </button>
            <button @click="sendTermKey('\x1b[Z')" title="Shift+Tab"
              class="h-8 px-3 rounded-lg text-xs font-mono bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              ⇧Tab
            </button>
            <button @click="sendTermKey('\x1b[A')" title="Arrow Up"
              class="h-8 px-2 rounded-lg text-xs bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              ↑
            </button>
            <button @click="sendTermKey('\x1b[B')" title="Arrow Down"
              class="h-8 px-2 rounded-lg text-xs bg-surface-800 border border-surface-600 text-surface-500 hover:text-white hover:border-surface-500 transition">
              ↓
            </button>
            <div class="flex-1" />
            <!-- Recording visualizer in terminal toolbar -->
            <div v-if="isRecording" class="flex items-end gap-px h-5 w-24">
              <div v-for="b in 16" :key="b" class="flex-1 rounded-sm bg-danger/60 transition-all duration-75"
                :style="{ height: micBars[b - 1] + 'px' }" />
            </div>
            <span v-if="isRecording" class="text-xs text-danger font-mono">{{ recordingTime }}</span>
            <span v-else-if="micStatus" class="text-xs text-surface-500 truncate max-w-48">{{ micStatus }}</span>
            <!-- Mic button -->
            <button @click="toggleMic()"
              :class="[
                'w-9 h-9 rounded-full flex items-center justify-center transition flex-shrink-0 border relative',
                isRecording
                  ? 'bg-danger border-danger/50 text-white'
                  : 'bg-surface-800 border-surface-600 hover:border-accent/50 hover:bg-surface-700 text-surface-500 hover:text-accent'
              ]">
              <svg v-if="!isRecording" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="1" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
              </svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- New session modal -->
    <Teleport to="body">
      <div v-if="showNewSession" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
        @click.self="showNewSession = false">
        <div class="bg-surface-900 border border-surface-700 rounded-2xl p-6 w-[380px] shadow-2xl animate-fade-in">
          <h2 class="text-sm font-bold text-white mb-4">New Session</h2>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-surface-500 mb-1">Session ID</label>
              <input v-model="newId" placeholder="main"
                class="focus-ring w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-white" />
            </div>
            <div>
              <label class="block text-xs font-medium text-surface-500 mb-1">CLI</label>
              <select v-model="newCli"
                class="w-full bg-surface-800 border border-surface-600 rounded-lg px-3 py-2 text-sm text-white">
                <option value="claude">Claude Code</option>
                <option value="codex">Codex</option>
                <option value="qwen">Qwen Code</option>
              </select>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button @click="showNewSession = false"
              class="px-4 py-2 rounded-lg text-sm text-surface-500 hover:text-white transition">Cancel</button>
            <button @click="createSession"
              class="px-4 py-2 rounded-lg text-sm font-medium text-white bg-accent hover:bg-accent-hover transition">Create</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
const inputText = ref('')
const isRecording = ref(false)
const micStatus = ref('')
const micLevel = ref(0)
const micBars = reactive(new Array(30).fill(3))
const recordingTime = ref('0:00')
let analyserCtx: AudioContext | null = null
let analyser: AnalyserNode | null = null
let analyserRAF: number = 0
let recordStartTime = 0
let recordTimerInterval: ReturnType<typeof setInterval> | null = null

function startAnalyser(stream: MediaStream) {
  analyserCtx = new AudioContext()
  const source = analyserCtx.createMediaStreamSource(stream)
  analyser = analyserCtx.createAnalyser()
  analyser.fftSize = 64
  source.connect(analyser)
  const data = new Uint8Array(analyser.frequencyBinCount)

  recordStartTime = Date.now()
  recordTimerInterval = setInterval(() => {
    const sec = Math.floor((Date.now() - recordStartTime) / 1000)
    recordingTime.value = `${Math.floor(sec / 60)}:${(sec % 60).toString().padStart(2, '0')}`
  }, 200)

  const tick = () => {
    if (!analyser) return
    analyser.getByteFrequencyData(data)
    // Overall level (0-1)
    let sum = 0
    for (let i = 0; i < data.length; i++) sum += data[i]
    micLevel.value = Math.min(1, (sum / data.length) / 128)

    // Spread to bars
    const barCount = 30
    for (let b = 0; b < barCount; b++) {
      const idx = Math.floor((b / barCount) * data.length)
      const val = data[idx] / 255
      micBars[b] = Math.max(2, Math.round(val * 22))
    }
    analyserRAF = requestAnimationFrame(tick)
  }
  tick()
}

function stopAnalyser() {
  if (analyserRAF) cancelAnimationFrame(analyserRAF)
  analyserRAF = 0
  analyser = null
  if (analyserCtx) { analyserCtx.close(); analyserCtx = null }
  if (recordTimerInterval) { clearInterval(recordTimerInterval); recordTimerInterval = null }
  micLevel.value = 0
  micBars.fill(3)
  recordingTime.value = '0:00'
}

// ── Send key to terminal via Agent Box API ──
function sendTermKey(key: string) {
  const s = useSessionsStore()
  if (!s.activeId) return
  const api = useApi()
  if (key === '\x03') {
    api.post(`/api/sessions/${s.activeId}/interrupt`)
  } else {
    api.post(`/api/sessions/${s.activeId}/send`, { text: key })
  }
}
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []

function sendMessage() {
  const text = inputText.value.trim()
  if (!text) return
  const sessions = useSessionsStore()
  if (!sessions.activeId) return
  const api = useApi()
  api.post(`/api/sessions/${sessions.activeId}/send`, { text })
  inputText.value = ''
}

function encodeWav(samples: Float32Array, sr: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const v = new DataView(buf)
  const wr = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }
  wr(0, 'RIFF'); v.setUint32(4, 36 + samples.length * 2, true); wr(8, 'WAVE'); wr(12, 'fmt ')
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true)
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
  wr(36, 'data'); v.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}

async function webmToWav(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext()
  const dec = await ctx.decodeAudioData(await blob.arrayBuffer())
  const wav = encodeWav(dec.getChannelData(0), dec.sampleRate)
  ctx.close()
  return wav
}

async function toggleMic() {
  if (isRecording.value) {
    mediaRecorder?.stop()
    return
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = async () => {
      isRecording.value = false
      stopAnalyser()
      stream.getTracks().forEach(t => t.stop())
      if (!audioChunks.length) { micStatus.value = ''; return }

      micStatus.value = 'Конвертирую...'
      const wav = await webmToWav(new Blob(audioChunks, { type: mediaRecorder!.mimeType }))

      micStatus.value = 'Распознаю...'
      try {
        const fd = new FormData()
        fd.append('audio', wav, 'recording.wav')
        const api = useApi()
        const data = await api.post<{ text?: string }>('/api/asr/transcribe', fd)
        if (data.text) {
          const sessions = useSessionsStore()
          if (sessions.activeId) {
            await api.post(`/api/sessions/${sessions.activeId}/send`, { text: data.text })
            const preview = data.text.length > 60 ? data.text.substring(0, 60) + '…' : data.text
            micStatus.value = '✓ ' + preview
          }
        } else {
          micStatus.value = 'Пустой ответ'
        }
      } catch {
        micStatus.value = 'Ошибка распознавания'
      }
      setTimeout(() => { micStatus.value = '' }, 4000)
    }
    mediaRecorder.start(250) // collect chunks every 250ms — no data loss on stop
    isRecording.value = true
    startAnalyser(stream)
  } catch {
    alert('Нет доступа к микрофону')
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
