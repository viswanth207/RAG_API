import React from 'react'
import '../cyber-theme.css'

function LandingPage({ onGetStarted }) {
  return (
    <div className="page active landing-page premium">
      {/* Abstract Noise Texture Overlay */}
      <div className="noise-overlay"></div>

      {/* Hero Section */}
      <section className="hero-section premium-hero">
        <div className="ambient-glow bg-blur"></div>
        <div className="container">
          <div className="hero-grid">
            <div className="hero-content-left">
              <div className="version-badge">
                <span className="node-dot pulse"></span>
                <span className="badge-text">Intelligence Gateway v1.0.4</span>
              </div>
              <h1 className="display-title">
                Unlock Your Data with the <br/>
                <span className="gradient-text-subtle">Intelligence Gateway</span>
              </h1>
              <p className="hero-subtext">
                The ultimate API bridge connecting private, distributed datasets to modern generative AI. 
                Infuse your production environments with contextual intelligence through secure, high-speed streaming.
              </p>
           
              <div className="hero-actions">
                <button className="btn-modern primary" onClick={onGetStarted}>
                  Initialize Gateway
                </button>
                <div className="protocol-status">
                  <div className="status-item"><span className="indicator solid"></span> RESTful</div>
                  <div className="status-item"><span className="indicator hollow"></span> SSE Stream</div>
                </div>
              </div>
            </div>

            <div className="hero-content-right" style={{ display: 'none' }}>
              {/* Removed code container */}
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="architecture-section">
        <div className="container">
          <div className="section-head">
            <h2 className="section-title">The Neural Architecture</h2>
            <p className="section-subtext">
              A high-security bridge designed for enterprise RAG and distributed datasets.
            </p>
          </div>

          <div className="arch-flow">
            <div className="arch-card">
              <div className="abstract-marker marker-source"></div>
              <h3 className="arch-title">Source Connection</h3>
              <p className="arch-desc">
                Link MongoDB, PostgreSQL, or Static JSON/CSV. Our engine creates a temporary 
                semantic map without ever importing your raw PII.
              </p>
            </div>

            <div className="flow-line"></div>

            <div className="arch-card primary-card">
              <div className="abstract-marker marker-vector"></div>
              <h3 className="arch-title">Contextual Vectoring</h3>
              <p className="arch-desc">
                Proprietary "Fresh Scan" technology vectors your data in real-time, 
                ensuring the AI always answers with live, production-accurate info.
              </p>
            </div>

            <div className="flow-line"></div>

            <div className="arch-card">
              <div className="abstract-marker marker-stream"></div>
              <h3 className="arch-title">SSE Propagation</h3>
              <p className="arch-desc">
                Answers are delivered via Server-Sent Events, providing ultra-low 
                latency responses that feel instant and organic.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="features-section">
        <div className="container">
          <div className="section-head">
            <h2 className="section-title">Developer Protocols</h2>
            <p className="section-subtext">
              Built by developers, for mission-critical production systems.
            </p>
          </div>

          <div className="bento-grid">
            <div className="bento-card">
              <div className="bento-visual viz-auth"></div>
              <h3 className="bento-title">Universal Auth</h3>
              <p className="bento-desc">
                JWT-backed identity management with API Key + Secret rotation. 
                Full support for Private Network headers and CORS whitelisting.
              </p>
            </div>

            <div className="bento-card">
              <div className="bento-visual viz-telemetry"></div>
              <h3 className="bento-title">Usage Telemetry</h3>
              <p className="bento-desc">
                Real-time tracking of token consumption, success rates, and 
                response latencies directly via the Developer Dashboard.
              </p>
            </div>

            <div className="bento-card card-wide">
              <div className="bento-content">
                <h3 className="bento-title">Cross-DB RAG</h3>
                <p className="bento-desc">
                  The only gateway allowing you to query across MongoDB and 
                  Postgres in a single contextual window. No data migration needed.
                </p>
              </div>
              <div className="bento-visual viz-rag"></div>
            </div>

            <div className="bento-card card-wide">
              <div className="bento-content">
                <h3 className="bento-title">SSE Streaming</h3>
                <p className="bento-desc">
                  Professional-grade stream parsing built in. Handle long-form 
                  AI responses without timing out your load balancer.
                </p>
              </div>
              <div className="bento-visual viz-stream"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Deployment Scenarios */}
      <section className="scenarios-section">
        <div className="container">
          <div className="section-head text-left">
            <h2 className="section-title">Deployment Scenarios</h2>
            <p className="section-subtext">Where the Intelligence Gateway powers the world.</p>
          </div>

          <div className="scenario-list">
            <div className="scenario-item">
              <div className="scenario-line"></div>
              <div className="scenario-content">
                <h3>Enterprise Search</h3>
                <p>Turn internal documentation and private databases into a secure chat interface for employees.</p>
              </div>
            </div>
            <div className="scenario-item">
              <div className="scenario-line"></div>
              <div className="scenario-content">
                <h3>SaaS Feature-Add</h3>
                <p>Add AI "Ask your data" features to your existing dashboard in less than 15 minutes of dev time.</p>
              </div>
            </div>
            <div className="scenario-item">
              <div className="scenario-line"></div>
              <div className="scenario-content">
                <h3>R&D Insights</h3>
                <p>Scan vast experimental datasets and ask for patterns, trends, and hypothetical predictions.</p>
              </div>
            </div>
            <div className="scenario-item">
              <div className="scenario-line"></div>
              <div className="scenario-content">
                <h3>DevOps Support</h3>
                <p>Interface with log databases and system metrics to diagnose complex production failures.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Premium CTA */}
      <section className="final-cta-section">
        <div className="container">
          <div className="cta-box">
            <div className="cta-glow"></div>
            <h2 className="cta-title">Ready to Connect your Data?</h2>
            <p className="cta-subtext">
              Join the alpha protocol and start building with the BRAIN.OS Intelligence Gateway today.
            </p>
            <button className="btn-modern primary large" onClick={onGetStarted}>
              Initialize Your Key
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

export default LandingPage


