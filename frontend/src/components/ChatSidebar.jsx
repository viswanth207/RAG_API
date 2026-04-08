import React from 'react'

function ChatSidebar({ 
  conversations, 
  currentConversationId, 
  onNewConversation, 
  onSwitchConversation, 
  onDeleteConversation,
  isOpen 
}) {
  return (
    <div className={`chat-sidebar ${isOpen ? '' : 'hidden'}`}>
      <div className="sidebar-header">
        <button className="btn btn-primary btn-small btn-block" onClick={onNewConversation}>
          + New Chat
        </button>
      </div>
      <div className="sidebar-content">
        {conversations.map(conversation => (
          <div
            key={conversation.id}
            className={`conversation-item ${conversation.id === currentConversationId ? 'active' : ''}`}
            onClick={() => onSwitchConversation(conversation.id)}
          >
            <span className="conversation-title">{conversation.title}</span>
            <button 
              className="conversation-delete" 
              onClick={(e) => onDeleteConversation(conversation.id, e)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ChatSidebar
