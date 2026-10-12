import { useState } from 'react'
import './App.css'
import LiveKitModal from './components/LiveKitModal';

function App() {
  const [showSupport, setShowSupport] = useState(false);

  const handleSupportClick = () => {
    setShowSupport(true)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">🏥</div>
            <span>EchoHealth</span>
          </div>
          <nav className="nav">
            <a href="#features">Features</a>
            <a href="#about">About</a>
          </nav>
        </div>
      </header>

      <main className="main">
        <section className="hero">
          <div className="hero-content">
            <h1 className="hero-title">
              A Safe Voice Companion for 
              <span className="gradient-text"> Reliable Medical Information</span>
            </h1>
            <p className="hero-subtitle">
              Get instant, evidence-based health information through voice conversation. 
              Powered by MEDLINE documents with safety-first design.
            </p>
            <button className="cta-button" onClick={handleSupportClick}>
              <span className="button-icon">🚀</span>
              Start Voice Conversation
            </button>
            <div className="hero-features">
              <div className="feature-item">
                <div className="feature-icon">🎤</div>
                <span>Voice-First</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">📚</div>
                <span>MEDLINE Sources</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">🛡️</div>
                <span>Safety-First</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">🔬</div>
                <span>Evidence-Based</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">📖</div>
                <span>Citations</span>
              </div>
              <div className="feature-item">
                <div className="feature-icon">⚡</div>
                <span>Real-Time</span>
              </div>
            </div>

            
          </div>
          
          <div className="hero-visual">
            <div className="floating-card">
              <div className="card-header">
                <div className="hero-status-dot"></div>
                <span>EchoHealth Assistant</span>
              </div>
              <div className="card-content">
                <div className="voice-wave">
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                  <div className="wave-bar"></div>
                </div>
                <p>Ready to help with your health questions</p>
              </div>
            </div>
          </div>
        </section>

        {/* <section className="info-section">
          <div className="info-grid">
            <div className="info-card">
              <h3>🔬 Evidence-Based</h3>
              <p>All responses sourced from trusted MEDLINE medical literature</p>
            </div>
            <div className="info-card">
              <h3>🎯 Safe & Responsible</h3>
              <p>No personal medical advice - always recommends professional consultation</p>
            </div>
            <div className="info-card">
              <h3>📖 Source Citations</h3>
              <p>Every response includes inline citations for transparency</p>
            </div>
          </div>
        </section> */}
      </main>

      {showSupport && <LiveKitModal setShowSupport={setShowSupport}/>}
    </div>
  )
}

export default App