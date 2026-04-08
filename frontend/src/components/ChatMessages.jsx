import React, { useEffect, useRef } from 'react'

function ChatMessages({ messages, assistantName, isLoading }) {
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const escapeHtml = (text) => {
    return text.replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/\n/g, '<br>')
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  return (
    <div className="chat-messages">
      {messages.length === 0 && !isLoading && (
        <div className="welcome-message">
          <div className="welcome-icon">🤖</div>
          <h3>Welcome!</h3>
          <p>Your assistant is ready. Ask me anything about your data!</p>
        </div>
      )}
      
      {messages.map((message, index) => {
        const avatar = message.role === 'user' ? '👤' : '🤖'
        const time = formatTime(message.timestamp)
        
        return (
          <div key={index} className={`message ${message.role}-message`}>
            <div className="message-avatar">{avatar}</div>
            <div className="message-content">
              <div 
                className="message-text"
                dangerouslySetInnerHTML={{ __html: escapeHtml(message.content) }}
              />
              <div className="message-meta">
                <span>{time}</span>
                {message.role === 'assistant' && message.sourcesUsed !== undefined && (
                  <span>• {message.sourcesUsed} sources</span>
                )}
              </div>
            </div>
          </div>
        )
      })}
      
      {isLoading && (
        <div className="message assistant-message thinking-message">
          <div className="message-avatar">🤖</div>
          <div className="message-content">
            <div className="message-text">
              <span className="thinking-dots">
                <span>.</span>
                <span>.</span>
                <span>.</span>
              </span>
            </div>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  )
}

export default ChatMessages
