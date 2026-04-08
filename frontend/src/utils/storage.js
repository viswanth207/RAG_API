const CONVERSATIONS_KEY = 'ai_assistant_conversations'

export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export function getAllConversations() {
  const stored = localStorage.getItem(CONVERSATIONS_KEY)
  return stored ? JSON.parse(stored) : {}
}

export function saveConversation(conversationId, conversationData) {
  const conversations = getAllConversations()
  conversations[conversationId] = conversationData
  localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations))
}

export function getConversation(conversationId) {
  const conversations = getAllConversations()
  return conversations[conversationId] || null
}

export function deleteConversationById(conversationId) {
  const conversations = getAllConversations()
  delete conversations[conversationId]
  localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations))
}
