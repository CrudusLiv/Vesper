export const initialState = {
  auth: { secret: null, unlocked: false },
  status: { integrations: {}, vault: {}, memory: 'ok', loading: false, error: null },
  chat: { messages: [], pending: false },
  memory: { query: '', results: [], loading: false, error: null },
  orb: 'idle',
}

export function reducer(state, action) {
  switch (action.type) {
    case 'UNLOCK':
      return { ...state, auth: { secret: action.secret, unlocked: true } }
    case 'LOCK':
      return { ...state, auth: { secret: null, unlocked: false } }
    case 'STATUS_LOADING':
      return { ...state, status: { ...state.status, loading: true, error: null } }
    case 'STATUS_OK':
      return { ...state, status: { ...action.status, loading: false, error: null } }
    case 'STATUS_ERROR':
      return { ...state, status: { ...state.status, loading: false, error: action.error } }
    case 'CHAT_SEND':
      return {
        ...state,
        chat: {
          messages: [...state.chat.messages, { role: 'user', content: action.content, ts: action.ts }],
          pending: true,
        },
        orb: 'thinking',
      }
    case 'CHAT_REPLY':
      return {
        ...state,
        chat: {
          messages: [...state.chat.messages, { role: 'assistant', content: action.reply, sources: action.sources, ts: action.ts }],
          pending: false,
        },
        orb: 'speaking',
      }
    case 'CHAT_ERROR':
      return {
        ...state,
        chat: {
          messages: [...state.chat.messages, { role: 'assistant', content: action.error, error: true, ts: action.ts }],
          pending: false,
        },
        orb: 'idle',
      }
    case 'MEMORY_QUERY':
      return { ...state, memory: { ...state.memory, query: action.query } }
    case 'MEMORY_LOADING':
      return { ...state, memory: { ...state.memory, loading: true, error: null } }
    case 'MEMORY_RESULTS':
      return { ...state, memory: { ...state.memory, results: action.results, loading: false } }
    case 'MEMORY_ERROR':
      return { ...state, memory: { ...state.memory, loading: false, error: action.error } }
    case 'SET_ORB':
      return { ...state, orb: action.orb }
    default:
      return state
  }
}
