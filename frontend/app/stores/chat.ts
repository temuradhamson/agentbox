import { defineStore } from 'pinia'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool_result'
  type: 'text' | 'tool_use' | 'tool_result' | 'thinking'
  content: string
  timestamp?: string
  tool_name?: string
  input?: any
  is_error?: boolean
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as ChatMessage[],
    connected: false,
    sessionId: null as string | null,
  }),

  actions: {
    clear() {
      this.messages = []
      this.sessionId = null
      this.connected = false
    },

    addMessage(msg: ChatMessage) {
      this.messages.push(msg)
    },

    setMessages(msgs: ChatMessage[]) {
      this.messages = msgs
    },
  },
})
