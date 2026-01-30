import { create } from 'zustand'
import type { StateCreator } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
  metrics?: {
    search_ms?: number
    llm_ms?: number
    total_ms?: number
  }
}

export interface Citation {
  chunk_id: string
  doc_id: string
  source: string
  page?: number
  sheet?: string
  slide?: number
  text: string
  score: number
}

interface ChatState {
  messages: ChatMessage[]
  isLoading: boolean
  currentSessionId: string | null
  
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateLastMessage: (content: string) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
  newSession: () => void
}

const chatStore: StateCreator<ChatState> = (set) => ({
  messages: [],
  isLoading: false,
  currentSessionId: null,
  
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) =>
    set((state: ChatState) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        },
      ],
    })),
  
  updateLastMessage: (content: string) =>
    set((state: ChatState) => {
      const messages = [...state.messages]
      if (messages.length > 0) {
        messages[messages.length - 1].content = content
      }
      return { messages }
    }),
  
  setLoading: (loading: boolean) => set({ isLoading: loading }),
  
  clearMessages: () => set({ messages: [] }),
  
  newSession: () =>
    set({
      messages: [],
      currentSessionId: crypto.randomUUID(),
    }),
})

export const useChatStore = create<ChatState>()(chatStore)
