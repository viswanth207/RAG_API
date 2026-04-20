import React, { useState, useEffect } from 'react'
import '../cyber-theme.css'

function ApiGatewayPage({ onHomeClick }) {
  const [activeTab, setActiveTab] = useState('gateway')
  const [usageStats, setUsageStats] = useState({ total_hits: 0, success_rate: 100, chart_data: Array(12).fill(0) })
  const [apiKey, setApiKey] = useState('')
  const [password, setPassword] = useState('')
  const [statusMsg, setStatusMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [dbName, setDbName] = useState('')
  const [remoteUrl, setRemoteUrl] = useState('')
  const [dbType, setDbType] = useState('mongodb')

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/v1/external/usage')
        const data = await res.json()
        if (res.ok) setUsageStats(data)
      } catch (err) { console.error("Usage Error", err) }
    }
    if (activeTab === 'usage') fetchStats();
  }, [activeTab])

  const generateRandomKey = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let result = 'sk_'
    for (let i = 0; i < 32; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setApiKey(result)
  }

  const generateCodeSnippet = () => {
    let friendUrl = remoteUrl;
    if (!friendUrl) {
      friendUrl = dbType === 'mongodb'
        ? "mongodb://10.178.40.87:27017"
        : "postgresql://user:pass@10.178.40.87:5432/dbname";
    }
    const dynamicBaseUrl = window.location.origin;
    return `// Copy this snippet into your 3rd-party integration
const BASE_URL = "${dynamicBaseUrl}";

// 1. Authenticate & Get Token
const getToken = async () => {
    try {
        const res = await fetch(\`\${BASE_URL}/api/v1/external/auth/token\`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: "${apiKey || 'library_assistant'}",
                password: "YOUR_SECRET"
            })
        });
        const data = await res.json();
        return data.access_token;
    } catch (e) {
        console.error("Auth Fail", e);
        return null;
    }
};

// 2. Chat with your Database (Professional Streaming Parser)
const chatWithDBStream = async (message, onChunk) => {
    const token = await getToken();
    if (!token) return;

    try {
        const res = await fetch(\`\${BASE_URL}/api/v1/external/chat/stream\`, {
            method: 'POST',
            headers: {
                "Authorization": \`Bearer \${token}\`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                database_name: "${dbName || 'library'}",
                database_url: "${friendUrl}",
                message: message
            })
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\\n');

            lines.forEach(rawLine => {
                const line = rawLine.trim();
                if (!line) return;

                try {
                    const cleanLine = line.startsWith('data: ') ? line.replace('data: ', '').trim() : line;
                    if (cleanLine === '[DONE]') return;
                    const parsed = JSON.parse(cleanLine);
                    if (parsed.type === 'content' && parsed.data) {
                        onChunk(parsed.data);
                    } else if (parsed.content) {
                        onChunk(parsed.content);
                    }
                } catch (e) {
                    if (!line.includes('{') && !line.startsWith('data:')) {
                        onChunk(line);
                    }
                }
            });
        }
    } catch (err) {
        console.error("Chat Stream Error:", err);
    }
};`;
  }

  const handleCopyCode = () => {
    const text = generateCodeSnippet();
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text);
    } else {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
      } catch (err) {
        console.error('Fallback copy error', err);
      }
      document.body.removeChild(textArea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegister = async (e) => {
    e.preventDefault()
    if (!apiKey) {
      setStatusMsg({ type: 'error', text: 'Please generate an API Key first.' })
      return
    }
    setLoading(true)
    setStatusMsg('')
    try {
      const res = await fetch('/api/v1/external/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey, password })
      })
      const data = await res.json()
      if (res.ok) {
        setStatusMsg({ type: 'success', text: 'Identity registered! Your Brain is now ready to scan remote databases.' })
      } else {
        setStatusMsg({ type: 'error', text: data.detail || "Registration failed." })
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: "Server connection failed." })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="cyber-wrapper">
      <nav className="cyber-sidebar">
        <div style={{ marginBottom: '3rem', padding: '0 10px', cursor: 'pointer' }} onClick={onHomeClick}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: '900', color: '#fff' }}>BRAIN<span style={{ color: 'var(--accent-primary)' }}>.</span>OS</h1>
        </div>
        <button className={`cyber-nav-item ${activeTab === 'gateway' ? 'active' : ''}`} onClick={() => setActiveTab('gateway')}>
          <span>Gateway Hub</span>
        </button>
        <button className={`cyber-nav-item ${activeTab === 'usage' ? 'active' : ''}`} onClick={() => setActiveTab('usage')}>
          <span>Usage Stats</span>
        </button>
        <button className={`cyber-nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          <span>Settings</span>
        </button>
        <button className={`cyber-nav-item ${activeTab === 'docs' ? 'active' : ''}`} onClick={() => setActiveTab('docs')}>
          <span>Docs</span>
        </button>
      </nav>

      <main className="cyber-content">
        <div className="header-section">
          <h2 className="header-title">
            {activeTab === 'gateway' ? 'Developer Hub' : activeTab === 'usage' ? 'Usage Metrics' : activeTab === 'docs' ? 'Documentation' : 'Hub Settings'}
          </h2>
          <p style={{ color: 'var(--text-dim)', marginTop: '8px' }}>
            {activeTab === 'gateway' ? 'Integrate intelligence directly into your production environment.' :
              activeTab === 'usage' ? 'Real-time performance and consumption tracking.' :
              activeTab === 'docs' ? 'Implementation and integration documents for developers.' :
                'Manage your global API configuration and secret keys.'}
          </p>
        </div>

        {activeTab === 'gateway' && (
          <div className="cyber-grid">
            <div className="cyber-card">
              <h3 className="card-title"> Identity Access</h3>
              <p className="cyber-label" style={{ marginBottom: '24px', textTransform: 'none' }}>Credentials for authentication</p>

              <form onSubmit={handleRegister}>
                <div className="cyber-group">
                  <label className="cyber-label">App ID (API Key)</label>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <input className="cyber-input" type="text" value={apiKey} placeholder="Click Generate" readOnly />
                    <button type="button" className="btn-primary" style={{ width: 'auto', padding: '0 20px', fontSize: '0.8rem' }} onClick={generateRandomKey}>
                      Generate
                    </button>
                  </div>
                </div>

                <div className="cyber-group">
                  <label className="cyber-label">Client Secret</label>
                  <input className="cyber-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Secret password" required />
                </div>

                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Registering...' : 'Create New Identity'}
                </button>

                {statusMsg && (
                  <div style={{ marginTop: '20px', padding: '14px', borderRadius: '12px', background: statusMsg.type === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', color: statusMsg.type === 'success' ? '#10b981' : '#ef4444', border: '1px solid rgba(255,255,255,0.05)', fontSize: '0.9rem' }}>
                    {statusMsg.text}
                  </div>
                )}
              </form>
            </div>

            <div className="cyber-card">
              <h3 className="card-title">Connection Protocol</h3>

              <div className="cyber-group">
                <label className="cyber-label">Select Engine</label>
                <div className="toggle-pill">
                  <button onClick={() => setDbType('mongodb')} className={`toggle-item ${dbType === 'mongodb' ? 'active' : ''}`}>MongoDB</button>
                  <button onClick={() => setDbType('postgresql')} className={`toggle-item ${dbType === 'postgresql' ? 'active' : ''}`}>PostgreSQL</button>
                </div>
              </div>

              <div className="cyber-group">
                <label className="cyber-label">Target DB Name</label>
                <input className="cyber-input" type="text" value={dbName} onChange={(e) => setDbName(e.target.value)} placeholder="e.g. library" />
              </div>

              <div className="cyber-group">
                <label className="cyber-label">Endpoint URL (Source)</label>
                <input className="cyber-input" type="text" value={remoteUrl} onChange={(e) => setRemoteUrl(e.target.value)} placeholder={dbType === 'mongodb' ? "mongodb://10.178.40.87:27017" : "postgresql://user:pass@10.178.40.87:5432/db"} />
              </div>

              <div className="code-container">
                <button className="copy-button" onClick={handleCopyCode}>
                  {copied ? 'Copied!' : 'Copy Code'}
                </button>
                <pre className="code-block" style={{ maxHeight: '200px', overflowY: 'auto', textAlign: 'left' }}>
                  <code>{generateCodeSnippet()}</code>
                </pre>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'usage' && (
          <div className="cyber-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
            <div className="cyber-card">
              <p className="cyber-label">Total API Hits</p>
              <h4 style={{ fontSize: '2.5rem', margin: '15px 0' }}>{usageStats.total_hits.toLocaleString()}</h4>
              <p style={{ color: '#10b981' }}>↑ Pulse Active</p>
            </div>
            <div className="cyber-card">
              <p className="cyber-label">Success Rate</p>
              <h4 style={{ fontSize: '2.5rem', margin: '15px 0' }}>{usageStats.success_rate}%</h4>
              <p style={{ color: '#10b981' }}>Healthy Pulse</p>
            </div>
            <div className="cyber-card">
              <p className="cyber-label">Power Consumption</p>
              <h4 style={{ fontSize: '2.5rem', margin: '15px 0' }}>{(usageStats.total_hits * 125).toLocaleString()}</h4>
              <p style={{ color: 'var(--accent-primary)' }}>Estimated Tokens</p>
            </div>
            <div className="cyber-card" style={{ gridColumn: 'span 3' }}>
              <h3 className="card-title">Consumption Over Time (12h)</h3>
              <div style={{ height: '200px', width: '100%', display: 'flex', alignItems: 'flex-end', gap: '8px', padding: '20px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px' }}>
                {usageStats.chart_data.map((c, i) => {
                  const max = Math.max(...usageStats.chart_data, 1);
                  return <div key={i} style={{ flex: 1, height: `${(c / max) * 100}%`, minHeight: '5%', background: 'linear-gradient(to top, var(--accent-primary), var(--accent-secondary))', borderRadius: '4px', opacity: c > 0 ? 0.8 : 0.2 }}></div>
                })}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="cyber-card" style={{ maxWidth: '800px' }}>
            <h3 className="card-title">Protocol Config</h3>
            <div className="cyber-group">
              <label className="cyber-label">Trusted Origins (CORS)</label>
              <input className="cyber-input" type="text" placeholder="http://localhost:3000, your-domain.com" />
            </div>
            <button className="btn-primary" style={{ marginTop: '20px' }}>Update Protocols</button>
          </div>
        )}

        {activeTab === 'docs' && (
          <div className="cyber-grid">
            <div className="cyber-card" style={{ gridColumn: 'span 2' }}>
              <h3 className="card-title">Intelligence Gateway Architecture</h3>
              <p style={{ color: 'var(--text-dim)', lineHeight: '1.7', marginBottom: '25px' }}>
                The <strong>BRAIN.OS API</strong> is a high-security bridge designed to connect your private, distributed datasets (MongoDB or PostgreSQL) directly to generative AI models without exposing your raw data to the public internet.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px' }}>
                <div>
                  <h4 style={{ color: 'var(--accent-primary)', marginBottom: '12px' }}>How it Works</h4>
                  <ul style={{ color: 'var(--text-dim)', fontSize: '0.9rem', paddingLeft: '18px', listStyleType: 'circle' }}>
                    <li style={{ marginBottom: '10px' }}><strong>Identity Link</strong>: Authenticate via a secure SK_ key and client secret.</li>
                    <li style={{ marginBottom: '10px' }}><strong>Real-Time Vectoring</strong>: Our engine performs a "fresh scan" of your database on every request.</li>
                    <li style={{ marginBottom: '10px' }}><strong>Contextual Streaming</strong>: We inject only the relevant records into the AI context window and stream the answer via Server-Sent Events (SSE).</li>
                  </ul>
                </div>
                <div>
                  <h4 style={{ color: 'var(--accent-primary)', marginBottom: '12px' }}>Who is it for?</h4>
                  <ul style={{ color: 'var(--text-dim)', fontSize: '0.9rem', paddingLeft: '18px', listStyleType: 'circle' }}>
                    <li style={{ marginBottom: '10px' }}><strong>SaaS Platforms</strong>: Provide AI-powered search over user-specific data.</li>
                    <li style={{ marginBottom: '10px' }}><strong>Enterprise IT</strong>: Build secure RAG (Retrieval-Augmented Generation) systems without data leaks.</li>
                    <li style={{ marginBottom: '10px' }}><strong>Developers</strong>: Eliminate the need to build complex vector pipeline management.</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="cyber-card">
              <h3 className="card-title">Quick Protocol</h3>
              <p className="cyber-label">Initialization Snippet</p>
              <div className="code-container" style={{ margin: '15px 0' }}>
                <pre className="code-block" style={{ fontSize: '0.75rem', padding: '15px' }}>
                  <code>
                    const brain = new OS("sk_...");<br />
                    await brain.connect("library_db");<br />
                    brain.ask("Analyze trends...");
                  </code>
                </pre>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                BRAIN.OS is currently in <strong>Developer Alpha</strong>. Enjoy unlimited access to standard streaming protocols.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default ApiGatewayPage;
